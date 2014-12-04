HA-Proxy as Frontend to Redis
======

This proposal is for security models 1 and 3


# Step 1 : get a self-signed PEM
~~~
openssl genrsa > private.key
openssl req -new -key private.key -out priv.csr
openssl x509 -req -days 3650 -in priv.csr -signkey private.key -out private.crt 
cat private.key private.crt > my.pem
~~~

# Step 2 : haproxy.cfg
~~~

defaults REDIS
 mode tcp
 timeout connect  4s
 timeout server  30s
 timeout client  30s

frontend ft_redis
#TODO edit_line for cf-agent
bind 0.0.0.0:6379 ssl crt /etc/haproxy/my.pem name redis
 default_backend bk_redis

backend bk_redis
 option tcp-check
 tcp-check send PING\r\n
 tcp-check expect string +PONG
# tcp-check send info\ replication\r\n
# tcp-check expect string role:master
 tcp-check send QUIT\r\n
 tcp-check expect string +OK
#TODO edit_line for cf-agent
 server R1 192.168.1.30:6379 check inter 1s
# server R1 172.16.24.20:6379 check inter 1s
~~~

# Step 3 : replace netcat by openssl
~~~
openssl s_client -connect ${reporthost}:6379
~~~
