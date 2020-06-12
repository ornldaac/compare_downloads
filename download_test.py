#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import aiohttp
import logging
import netCDF4
import datetime
import hashlib
from functools import partial
from aiohttp import web, http_exceptions
from download_common import download_test_files, my_test_validator

if __name__ == "__main__":
    # set up some logging
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel(logging.INFO)
    HANDLER = logging.StreamHandler(sys.stdout)
    HANDLER.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s"))
    HANDLER.setLevel(logging.INFO)
    LOGGER.addHandler(HANDLER)

    start_time = datetime.datetime.now()

    # download all of the files
    now = datetime.datetime.now()
    LOGGER.debug("Started at " + now.strftime("%Y-%m-%d %H:%M:%S"))

    test_files = [
        "ornldaac_requests_ncss_csv.json",
        "ornldaac_requests_ncss_netcdf.json",
        "ornldaac_requests_ncss_ds1225_diffdata_csv.json",
        "ornldaac_requests_ncss_ds1225_diffdata_netcdf.json",
        "ornldaac_requests_ncss_ds1225_samedata_csv.json",
        "ornldaac_requests_ncss_ds1225_samedata_netcdf.json",
        "podaac_requests_ncss_samedata_csv.json",
        "podaac_requests_ncss_samedata_netcdf.json",
    ]

    # load file containing the list of download URLs, destination filenames, and layers
    current_dir = os.path.dirname(__file__)

    for test_file in test_files:

        LOGGER.info(f"start {test_file}")
        test_start = datetime.datetime.now()
        filepath = os.path.join(current_dir, test_file)

        with open(filepath, mode="r") as json_file:
            download_files = json.load(json_file)

        # set the desired concurrency level
        concurrency_level = 2

        LOGGER.info(f"Concurrency level is {concurrency_level}")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            download_test_files(
                loop,
                current_dir,
                download_files,
                my_test_validator,
                concurrency_level,
                LOGGER,
            )
        )

        test_end = datetime.datetime.now()
        test_elapsed = test_end - test_start

        LOGGER.info(f"finish {test_file} elapsed time {test_elapsed}")

    end_time = datetime.datetime.now()

    LOGGER.info("Ended at " + end_time.strftime("%Y-%m-%d %H:%M:%S"))
    LOGGER.info("Elapsed time " + str(end_time - start_time))
