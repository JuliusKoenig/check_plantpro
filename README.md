
# check_plantpro

is a small Nagios plugin which can be used to monitor a 'PlantWatchPRO' from Carel. 

**Tested with Python3.11**

Below is an overview of the parameters:

    usage:  check_plantpro.py  [-h] [-H HOST] [-p PORT] [-t TIMEOUT] [-e ENCODING] [-u USER] [-P PASSWORD] [-v] [-V] [-w WARNING] [-c CRITICAL] [-s FILTER]
    
    options:  
    -h,             --help show this help message and exit
    -H HOST,        --host HOST Hostname or Ipaddress
    -p PORT,        --port PORT Port
    -t TIMEOUT,  	--timeout TIMEOUT  HTTP Timeout
    -e ENCODING,  	--encoding ENCODING  Encoding for Web-scrapping
    -u USER,        --user USER Auth pser
    -P PASSWORD, 	--password PASSWORD  Auth password  
    -v, 	        --verbose Verbose
    -V,  	        --version Version
    -w WARNING,  	--warning WARNING  Warning Threshold
    -c CRITICAL,  	--critical CRITICAL  critical Threshold
    -f FILTER,  	--filter FILTER  Filter by sensor name.  For example: 'I/O-Modul  1.Kuehlung'

