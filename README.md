# sfo

## How to use

only read meta now.

``` py
import sfo.SfoFile as SfoFile
sfo = SfoFile.from_reader(reader) # or SfoFile.from_bytes(buffer)
content_id = sfo['CONTENT_ID']
```

## Thanks

Data struct is from this website: http://www.psdevwiki.com/ps3/PARAM.SFO