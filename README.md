# wpt_h1vsh2
This is a simple script which uses [webpagetest](https://www.webpagetest.org/) to compare core performance metrics of a page with HTTP/1.1 and HTTP/2. The script will default to using public webpagetest ([API key needed](https://www.webpagetest.org/getkey.php)), but can be configured to use a [private instance](https://sites.google.com/a/webpagetest.org/docs/private-instances).

Private instances are recommended since they can perform tests with many runs (public webpagetest limits each test to 9 runs).

## Instructions
The script needs global variables that define the webpagetest host and the location to test from.  If using public webpagetest, the API key will also be necessary:

```python
# full WPT hostname, ex: https://www.webpagetest.org
WPT_HOST = 'https://www.webpagetest.org'

# location name, from getTesters.php
WPT_LOC = 'Dulles'

# if using public webpagetest, put mandatory API key here
WPT_KEY = None
```

Once configured with the right host and location (and API key, if necessary), the test will prompt the user for test parameters:

```
$ python wpt_h1vsh2.py
Bandwidth down in Kbps[5000]:
Bandwidth up in Kbps[1000]:
latency in msec[40]:
packet loss ratio in %[0]:
test label, will be prepended with "h1_" and "h2_"[test_site]:
Number of runs (9 max with public WPT_HOST, more possible with private)[9]:
URL to test[https://www.google.com]:
Browser (Chrome or Firefox)[Chrome]:
Name of output pdf file[wpt_output.pdf]:
```

The output of the test is a PDF file with scatter plots of all core metrics.  The default metrics collected are stored in the global `METRICS` parameter:

```python
METRICS = ['render', 'firstPaint', 'domContentLoadedEventStart', 'domContentLoadedEventEnd',
  'lastVisualChange', 'visualComplete', 'docTime', 'loadTime', 'fullyLoaded', 'SpeedIndex',
  'bytesOutDoc', 'bytesOut', 'bytesInDoc', 'bytesIn', 'effectiveBpsDoc', 'effectiveBps']
```

The script will also output URLs pointing to webepagetest's video comparison and metrics comparison plot reports.

Outside of catching some very basic errors, there's not a lot of error checking or validation.

## Requirements
See `requirements.txt` file

## Example usage on Ubuntu 16.04 Server (No X11)

1. https://raw.githubusercontent.com/fastlyhoo/wpt_h1vsh2/master/wpt_h1vsh2.py
2. Add a snippet to the VERY beginning (line 1) of the script since you're not running a window manager (X11) and matlabplot will error on you because it assumes you are

```
############## BEGIN SERVER-COMPATIBILITY BLOCK ############
# Add this to the beginning of wpt_h1vsh2.py to use it on a server (without X11)
import matplotlib
matplotlib.use('Agg')
############## END SERVER-COMPATIBILITY BLOCK ##############
```

3. apt-get install python-pip python-tk
4. pip install -U pip setuptools
5. pip install matplotlib requests seaborn
6. get your api key from [https://www.webpagetest.org/getkey.php](https://www.webpagetest.org/getkey.php) and copy it into your wpt_h1vsh2.py (example: WPT_KEY = 'A.2348902482728395072')
7. Run **python wpt_h1vsh2.py** and enter your values when prompted
