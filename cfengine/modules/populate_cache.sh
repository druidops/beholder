#!/bin/bash
umask 277

function usage(){
echo no usage yet
}

function get_params()
{
local GETOPT_TEMP
#[ $# -eq 0 ] && usage
GETOPT_TEMP=$(getopt --alternative --longoptions \
  'help,securitymodel:,reporthost:,timeout:,port:,pipeline' 'h' "$@")

eval set -- "$GETOPT_TEMP"
while true ; do
  case "$1" in
    --securitymodel) securitymodel="$2"; shift 2 ;;
    --reporthost) reporthost=$2; shift 2 ;;
    --timeout) timeout=$2; shift 2 ;;
    --port) port=$2; shift 2 ;;
    --help|-h) usage ; break ;;
    --pipeline) pipeline=1 ; shift ;;
    --) shift ; break ;;
    *) echo "Options non traitees (bug?)" ; exit 1 ;;
  esac
done

# default to no security
[ -z "$securitymodel" ] 	&& securitymodel=0
[ -z "$timeout" ] 		&& timeout=10 # 10s
[ -z "$verbose" ] 		&& verbose=0
[ -z "$pipeline" ] 		&& pipeline=0
[ -z "$port" ] 			&& port="6379"

# default to cfengine policy server
if [ -z "$reporthost" ]; then
  if [ -f "/var/cfengine/policy_server.dat" ] ; then
    reporthost=$(cat /var/cfengine/policy_server.dat)
    [ ${verbose} -eq 1 ] && echo "fallback to policy hub [${reporthost}] for reporting"
  else
    echo "reporthost can't be set"
    exit 1
  fi
fi

# only binary required : netcat/s_client depending on securitymodel
case $securitymodel in
  0)
    transport='nc'
    ;;
  1)

    transport='s_client'
    ;;
  2)
    transport='nc'

    ;;
  3)
    transport='s_client'
    ;;
  *)
    echo "securitymodel have to be set"
    exit 1

esac

    [ ${verbose} -eq 1 ] && echo securitymodel=${securitymodel}
    [ ${verbose} -eq 1 ] && echo transport=${transport}
    [ ${verbose} -eq 1 ] && echo timeout=${timeout}

}
#report dependancy check
get_params "$@"

    if ! which "${transport}" >/dev/null 2>/dev/null ; then
      echo "+populate_cache_${transport}_not_present"
      exit 1
    fi

    h=$(uname -n)
    # redis targeting host
    outgoing_dir="/var/cfengine/outgoing"
    # test
    [ -d "${outgoing_dir}" ] || exit 1
    # check size
    alldatasize=$(du -skD ${outgoing_dir} | awk '{print $1}')
    # keep good performance: alldatasize * hosts < redis ramsize
    if [ "${alldatasize}" -ge 1024 ]; then
      echo "+populate_cache_outgoing_dir_too_big"
      exit 1
    fi

    # http://www.pixelbeat.org/scripts/timeout
	cleanup()
	{
    	trap - ALRM               #reset handler to default
	    kill -ALRM "${a}" 2>/dev/null #stop timer subshell if running
	    kill "$!" 2>/dev/null &&    #kill last job
	      exit 124                #exit with 124 if it was running
	}
    watchit()
    {
      trap "cleanup" ALRM
      sleep "${timeout}"& wait
      kill -ALRM $$
    }

    function interact_redis
    {
      raw_data="$1"
      if [ -n "${timeout}" ]; then
        # start the timer subshell and save its pid
        watchit& a=$!
        # cleanup after timeout
        trap "cleanup" ALRM INT
        # start the job wait for it and save its return value
        echo -en "${raw_data}"  |
          nc -w3 "${reporthost}" "${port}" > /dev/null 2>/dev/null &
        wait "$!"; ret=$?
        # send ALRM signal to watcherand wait for it to finish
        kill -ALRM "${a}"
        wait "${a}"
      else
         echo -en "${raw_data}"  |
        nc -w3 "${reporthost}" "${port}" > /dev/null 2>/dev/null
        ret=$?
      fi
      # return the value
      return $ret
    }
    # hack
#    /var/cfengine/bin/cf-promises -v| awk '/(Additional|Hard) classes/ {for (i=7;i<=NF-1;i++) {print $i}} /Discovered hard classes/ {for (i=4;i<=NF-1;i++) {print $i}}' > /tmp/cf3_classes 2>/dev/null
    #main
    files=( $(find ${outgoing_dir} -xtype f) )
    key=""
    pipe_str=""
    date=$(date +%s)
    for f in "${files[@]}"
    do
      suffix=${f:23} # strip off /var/cfengine/outgoing/
      [ "${suffix}" = "" ] && continue
      key="${h}#${suffix}"
      data=$(cat "${f}" | bzip2 -c  | openssl enc -base64 | tr -d '\n' )
      data_mstat=$(stat -c %Y -L ${f} )
      data_md5=$(md5sum ${f} | cut -c-32 )
      if [ "${pipeline}" -eq 0 ] ; then
        interact_redis "SET ${key} \"${data} ${date} ${data_mstat} ${data_md5}\" EX 3600\r\n QUIT\r\n" || echo "+populate_cache_network_link_error"
      else
        pipe_str="${pipe_str}$(echo -e "SET $key \"${data} ${date} ${data_mstat} ${data_md5}\" EX 3600")\r\n"
      fi
    done

    if [ "${pipeline}" -eq 1 ] ; then
      pipe_str="${pipe_str}QUIT\r\n"
      interact_redis "${pipe_str}" || echo "+populate_cache_network_link_error"
    fi

