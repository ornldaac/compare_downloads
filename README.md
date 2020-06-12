# Pair of test programs to compare successive downloads from thredds server

## input files
1)  `appeears_requests_ncss_csv.json` - 20 thredds urls with csv output
1)  `appeears_requests_ncss_netcdf.json` - 20 thredds urls with netcdf output

## scripts

1) `download_base.py` will download all 40 urls with names like `basexx.ext`
1) `download_test.py` will download all 40 urls with names like `testxx.ext`
and compare to base files.  If there are any differences program will abort.

## instructions

Run `download_base.py` first to build list of base downloads to be used for comparison later

Run `download_test.py` as many times as you want to confirm you always get the exact same download