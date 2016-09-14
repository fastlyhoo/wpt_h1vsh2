import re
import sys
import time
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import requests
import seaborn as sns


# full WPT hostname, ex: https://www.webpagetest.org
WPT_HOST = 'https://www.webpagetest.org'

# location name, from getTesters.php
WPT_LOC = 'Dulles'

# if using public webpagetest, put mandatory API key here
WPT_KEY = None

# metrics to gather and plot
METRICS = ['render', 'firstPaint', 'domContentLoadedEventStart', 'domContentLoadedEventEnd', 'lastVisualChange', 'visualComplete', 'docTime', 'loadTime', 'fullyLoaded', 'SpeedIndex', 'bytesOutDoc', 'bytesOut', 'bytesInDoc', 'bytesIn', 'effectiveBpsDoc', 'effectiveBps']

def get_wpt_script(browser, protocol, url):
    # prepare WPT scripts for Chrome and Firefox
    script = ""
    if protocol == 'h1' and browser == 'Firefox':
        script = "firefoxPref\tnetwork.http.spdy.enabled.http2\tfalse\n"
    script = "navigate\t%s" % url
    return script


def get_wpt_command_line(browser, protocol):
    # for h1, Chrome needs a command line variable
    if protocol == 'h1' and browser == 'Chrome':
        return "--disable-http2"
    return None


def submit_tests(protocols, params, label, browser, url):
    # submit tests to WPT and return the created test IDs
    api_url = '%s/runtest.php' % WPT_HOST
    test_ids = {}
    for proto in protocols:
        params['label'] = '%s_%s' % (proto, label)
        params['script'] = get_wpt_script(browser, proto, url)
        params['cmdline'] = get_wpt_command_line(browser, proto)
        print "submitting test for %s..." % proto
        response = requests.get(api_url, params=params, allow_redirects=False)

        # check for common errors
        if "(missing API key)" in response.text:
            print "Error: missing API key"
            sys.exit(1)
        elif "Invalid Location" in response.text:
            print "Error: invalid location '%s'" % WPT_LOC
            sys.exit(1)
        if 'location' not in response.headers:
            print "unknown error, test API URL manually: %s " % response.url
            sys.exit(1)

        test_id = get_test_id(response)
        test_ids[proto] = test_id
        print "   test submitted, test_id = %s" % test_id
    return test_ids


def get_wpt_result_urls(test_ids):
    # build URLs for WPT's video comparison and metrics comparison reports
    tests = ','.join("%s-l:%s" % (tid, p) for p, tid in test_ids.items())
    wpt_graph_url = "%s/graph_page_data.php?tests=%s" % (WPT_HOST, tests)
    wpt_video_url = "%s/video/compare.php?tests=%s" % (WPT_HOST, tests)
    return wpt_graph_url, wpt_video_url


def get_test_id(response):
    # extract test IDs from WPT's response to test submission
    # test IDs are in the Location HTTP header in redirects from WPT
    location = response.headers['location']
    if re.search('test\=([^,]+)', location):
        return re.search('test\=([^,]+)', location).group(1)
    else:
        return re.search('.*\/([^\/]+)\/', location).group(1)


def check_test_status(test_ids):
    # periodically check whether the tests are done
    # one check every 10 seconds
    for proto, test_id in test_ids.iteritems():
        print 'checking status for %s test (test_id = %s)' % (proto, test_id)
        result_url = "%s/jsonResult.php?test=%s" % (WPT_HOST, test_id)
        while True:
            result_json = requests.get(result_url).json()
            result_status = result_json['statusCode']
            if result_status != 200:
                print '   results not ready yet, waiting 10 seconds...'
                time.sleep(10)
            else:
                print '   results ready!'
                break


def get_wpt_stats(test_id):
    # get the json-formatted tests results from WPT for a given test ID
    stats = {}
    result_url = "%s/jsonResult.php?test=%s" % (WPT_HOST, test_id)
    results_data = requests.get(result_url).json()['data']
    for run, results in results_data['runs'].iteritems():
        run = int(run)
        stats[run] = {}

        run_results = results['firstView']
        for metric in METRICS:
            stats[run][metric] = run_results.get(metric, 0)
    return stats


def fetch_results(test_ids):
    # get the results for each test ID and build a dictionary of all results
    results = {}
    for protocol, test_id in test_ids.iteritems():
        print "fetching results for %s..." % test_id
        results[protocol] = get_wpt_stats(test_id)
    return results


def get_plot_dict(results):
    # convert results dictionary to a dictionary that can be easily consumed by write_pdf function
    plot_dict = {}
    for protocol, runs in results.iteritems():
        for run, metric_values in runs.iteritems():
            for metric in METRICS:
                plot_dict.setdefault(metric, {})
                plot_dict[metric].setdefault('runs', [])
                if run not in plot_dict[metric]['runs']:
                    plot_dict[metric]['runs'].append(run)
                plot_dict[metric].setdefault(protocol, [])
                plot_dict[metric][protocol].append(metric_values[metric])
    return plot_dict


def write_pdf(file_name, plot_dict):
    # plot results and create output PDF file
    with PdfPages(file_name) as pdf:
        for metric in METRICS:
            results = plot_dict[metric]
            x = results['runs']
            h1 = results['h1']
            h2 = results['h2']
            plt.figure(figsize=(8, 6))
            plt.scatter(x, h1, c='red')
            plt.scatter(x, h2, c='blue')
            plt.xlabel('run', fontsize=10)
            plt.ylabel('value', fontsize=10)
            plt.title(metric)
            plt.legend(['h1', 'h2'], bbox_to_anchor=(1, 0.5), loc=2)
            pdf.savefig()
            plt.close()


def main():
    # key test parameters for WPT API calls
    # documented here: https://sites.google.com/a/webpagetest.org/docs/advanced-features/webpagetest-restful-apis
    params = {
        'k': WPT_KEY,
        'private': 1,    # 1 for private, 0 for public
        'ignoreSSL': 1,  # 1 to ignore SSL errors, 0 to not
        'video': 1,      # 1 to capture video, 0 to not
        'tcpdump': 1,    # 1 to capture pcap, 0 to not
        'fvonly': 1,     # 1 to do first view only, 0 to do first and repeat.
                         # This script only looks at first view results
    }

    # check to see if we're using public WPT and if so, make sure we have an API key
    if 'www.webpagetest.org' in WPT_HOST and WPT_KEY is None:
        print "Must use API key with public webpagetest.  Edit script and add key to global WPT_KEY variable"
        sys.exit(1)

    params['bwDown'] = raw_input('Bandwidth down in Kbps[5000]:') or 5000
    params['bwUp'] = raw_input('Bandwidth up in Kbps[1000]:') or 1000
    params['latency'] = raw_input('latency in msec[40]:') or 40
    params['plr'] = raw_input('packet loss ratio in %[0]:') or 0
    label = raw_input('test label, will be prepended with ' +
        '"h1_" and "h2_"[test_site]:') or 'test_site'
    params['runs'] = raw_input(
        'Number of runs (9 max with public WPT_HOST, ' +
        'more possible with private)[9]:') or 9

    url = raw_input(
        'URL to test[https://www.google.com]:') or 'https://www.google.com'
    browser = raw_input('Browser (Chrome or Firefox)[Chrome]:') or 'Chrome'
    params['location'] = '%s:%s.custom' % (WPT_LOC, browser)

    output_pdf_file = raw_input(
        'Name of output pdf file[wpt_output.pdf]:') or "wpt_output.pdf"

    # submit tests and wait for results
    test_ids = submit_tests(('h1', 'h2'), params, label, browser, url)
    check_test_status(test_ids)
    results = fetch_results(test_ids)

    # plot results and create PDF file
    print "preparing PDF file..."
    plot_dict = get_plot_dict(results)
    write_pdf(output_pdf_file, plot_dict)
    print "PDF file created"

    #WPT URLs for video comparison and scatter plots
    wpt_graph_url, wpt_video_url = get_wpt_result_urls(test_ids)
    print "WPT result URLs"
    print "==============="
    print "WPT plots URL: %s" % wpt_graph_url
    print "WPT video comparison URL: %s" % wpt_video_url
    print "==============="
    print "finished!"


if __name__ == '__main__':
    rval = main()
    sys.exit(rval)
