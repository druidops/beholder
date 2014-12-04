# secure model 0
populate_cache(clear) --TCP--> redis(clear)

Pros:
---
  * immediatly works out of the box

Cons:
---
  * redis is exposed
  * no auth
  * datas are transmited in clear


# secure model 1
Also known as a the lame ssl terminator

populate_cache(clear) s_connect --TCP/ssl--> haproxy --> redis(clear)

Pros:
---
  * SSL
  * auth is possible via client certificates

Cons:
---
  * add a dependency (ssl server)

# secure model 2
populate_cache(hybrid-crypto) --TCP--> redis(crypted)

Pros:
---
  * encrypted data in redis

Cons:
---
  * redis exposed
  * name of keys exposed (hostnames)

# secure model 3
By the way, model 1+2 = model 3
populate_cache(hybrid-crypto) s_connect --TCP/ssl--> haproxy --> redis(crypted)


Pros:
---
  * see secure models 1 and 2

Cons:
---
  * complexity

# secure model 4
To be defined, here some clues :
  * hybrid-crypto enabled on demand
  * ssl enabled on demand (really ???)
  * drop layer 4 support, provide app-level API with OAuth2 (bye bye netcat :) )
