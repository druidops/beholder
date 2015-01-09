#!/bin/bash
umask 277

VERSION="0.2"

function usage()
{
  echo "[${VERSION}]"
  echo "Usage: populate_cache.sh [option]"
  echo "Compress and send outgoing linked files to REDIS server"
  echo ""
  echo "  -h, --help                 print this usage and exit"
  echo "  -v, --verbose              verbose mode [0-1] (default:0)"
  echo "  -d, --debug                debug mode [0-1] (default:0)"
  echo "  -P, --pipelining           pipelining mode [0-1] (default:0)"
  echo "  -p, --port=<port>          remote port number (default:6379)"
  echo "  -r, --reporthost=<host>    REDIS server address (default:policy_server)"
  echo "  -s, --securitymodel=<n>    security model number [0-3] (default:0)"
  echo "  -t, --timeout=<n>          timeout command (default:10s)"
  echo "  -o, --outgoing=<directory> outgoing directory path (default:/var/cfengine/outgoing)"
  echo "  -T, --ttl=<secs>           ttl value (default:3600)"
  echo "  -l, --list                 list outgoing files"
  echo
}

function get_params()
{
  local GETOPT_TEMP

  GETOPT_TEMP=$(getopt -o vhdPls:r:t:p:o: --long \
  verbose,help,debug,pipelining,list,securitymodel:,reporthost:,timeout:,port:,outgoing:,ttl: -n 'populate_cache.sh' -- "$@")

  if [ $? != 0 ] ; then echo "getopt error, terminating..." >&2 ; exit 1 ; fi

  eval set -- "$GETOPT_TEMP"

  while true ; do
    case "$1" in
      -v | --verbose )      verbose=1;          shift ;;
      -h | --help)          usage;              exit  0;;
      -d | --debug)         debug=1;            shift ;;
      -s | --securitymodel) securitymodel="$2"; shift 2;;
      -r | --reporthost)    reporthost=$2;      shift 2;;
      -t | --timeout)       timeout=$2;         shift 2;;
      -p | --port)          port=$2;            shift 2;;
      -o | --outgoing)      outgoing_dir=$2;    shift 2;;
      -T | --ttl)           ttl=$2;             shift 2;;
      -P | --pipelining)    pipelining=1;       shift ;;
      -l | --list)          get_list_files=1;   shift ;;
      --)                   shift;              break ;;
      *) echo "Incorrect Option [$1]";          break ;;
    esac
  done

  : "${securitymodel:=0}"
  : "${timeout:=10}" # 10s
  : "${debug:=0}"
  : "${verbose:=${debug}}"
  : "${pipelining:=0}"
  : "${get_list_files:=0}"
  : "${port:=6379}"
  : "${ttl:=3600}"
  : "${outgoing_dir:=/var/cfengine/outgoing}"
  : "${HOSTNAME:=$(uname -n)}"

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

  if [ "${verbose}" -ge 1 ]; then
    echo "Security model is (${securitymodel})"
    echo "Tranport is (${transport})"
    echo "Timeout command set to (${timeout}s)"
    echo "Pipelining set to ${pipelining}"
    echo "TCP port: (${port})"
    echo "value ttl: (${ttl})"
  fi
}

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

connect_to_redis()
{
  local r="$1"
  local p="$2"

  case ${transport} in
    nc)
      nc -w3 "${r}" "${p}" ;;
    s_client)
      openssl s_client -connect "${r}:${p}" ;;
    *)
      usage; exit 1
  esac
}

function send_raw_data_to_redis
{
  [ -z "${raw_data}" ] && return
    # start the timer subshell and save its pid
    watchit& a=$!
    # cleanup after timeout
    trap "cleanup" ALRM INT
    # start the job wait for it and save its return value
    [ "${verbose}" -ge 1 ] && echo "send_raw_data_to_redis: data(${#raw_data})"
    echo -en "${raw_data}"  |
     connect_to_redis "${reporthost}" "${port}"   > /dev/null 2>/dev/null &
    wait "$!"; ret=$?
    # send ALRM signal to watcherand wait for it to finish
    kill -ALRM "${a}"
    wait "${a}"
  # return the value
  return $ret
}

# main
get_params "$@"

# outgoing dir check
if [ ! -d "${outgoing_dir}" ]; then
  echo "Error: outgoing_dir=[${outgoing_dir}] not exists"
  exit 1
elif [ "${verbose}" -ge 1 ]; then
  echo "outgoing_dir=[${outgoing_dir}] exists"
fi

list_of_files=( $(find "${outgoing_dir}" -xtype f) )
if [ $? -ne 0 ]; then
  echo "Error: cmd=[find ${outgoing_dir} -xtype f]" >&2
  exit 1
fi

if [ "${get_list_files}" -eq 1 -o "${verbose}" -ge 1 ]; then
  echo "Outgoing files in [${outgoing_dir}]:"
  printf ' %s\n' "${list_of_files[@]}";
  [ "${get_list_files}" -eq 1 ] && exit 0
fi

# redis targeting host (default to cfengine policy server)
if [ -z "$reporthost" ]; then
  if [ -f "/var/cfengine/policy_server.dat" ] ; then
    reporthost=$(cat /var/cfengine/policy_server.dat)
    [ ${verbose} -ge 1 ] && echo "fallback to policy hub [${reporthost}] for reporting"
  else
    echo "reporthost can't be set"
    exit 1
  fi
fi

if ! which "${transport}" >/dev/null 2>/dev/null ; then
  echo "+populate_cache_${transport}_not_present"
  exit 1
fi

# check size
alldatasize=$(du -skD "${outgoing_dir}" | awk '{print $1}')

# keep good performance: alldatasize * hosts < redis ramsize
if [ "${alldatasize}" -ge 1024 ]; then
  echo "+populate_cache_outgoing_dir_too_big"
  exit 1
fi

# hack
# /var/cfengine/bin/cf-promises -v| awk '/(Additional|Hard) classes/ {for (i=7;i<=NF-1;i++) {print $i}} /Discovered hard classes/ {for (i=4;i<=NF-1;i++) {print $i}}' > /tmp/cf3_classes 2>/dev/null

key=""
raw_data=""
date=$(date +%s)

for f in "${list_of_files[@]}"
do
  suffix=${f:23} # strip off /var/cfengine/outgoing/
  [ "${suffix}" = "" ] && continue
  key="${HOSTNAME}#${suffix}"
  data=$(bzip2 -c < "${f}" | openssl enc -base64 | tr -d '\n' )
  data_mstat=$(stat -c %Y -L ${f} )
  data_md5=$(md5sum ${f} | cut -c-32 )
  if [ "${pipelining}" -eq 0 ] ; then
    raw_data="SET ${key} \"${data} ${date} ${data_mstat} ${data_md5}\" EX ${ttl}\r\n QUIT\r\n"
    if send_raw_data_to_redis ; then
      :
    else
      [ "${debug}" -ge 1 ] && echo "transport ${transport} failed with raw_data=[${raw_data}]"
      [ "${verbose}" -ge 1 ] && echo "transport ${transport} failed"
      echo "+populate_cache_network_link_error"
      exit 1
    fi
  else
    raw_data="${raw_data}$(echo -e "SET $key \"${data} ${date} ${data_mstat} ${data_md5}\" EX ${ttl}")\r\n"
  fi
done

if [ "${pipelining}" -eq 1 ] ; then
  raw_data="${raw_data}QUIT\r\n"
  if send_raw_data_to_redis ; then
    :
  else
    [ "${debug}" -ge 1 ] && echo "transport ${transport} failed with raw_data=[${raw_data}]"
    [ "${verbose}" -ge 1 ] && echo "transport ${transport} failed"
    echo "+populate_cache_network_link_error"
    exit 1
  fi
fi

