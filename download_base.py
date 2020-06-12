#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
import datetime
from download_common import download_base_files, my_base_validator

if __name__ == "__main__":
    # set up some logging
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel(logging.DEBUG)
    HANDLER = logging.StreamHandler(sys.stdout)
    HANDLER.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s"))
    HANDLER.setLevel(logging.DEBUG)
    LOGGER.addHandler(HANDLER)

    start_time = datetime.datetime.now()

    # download all of the files
    LOGGER.debug("Started at " + start_time.strftime("%Y-%m-%d %H:%M:%S"))

    base_files = [
        "ornldaac_requests_ncss_csv.json",
        "ornldaac_requests_ncss_netcdf.json",
        "ornldaac_requests_ncss_ds1225_diffdata_csv.json",
        "ornldaac_requests_ncss_ds1225_diffdata_netcdf.json",
        "ornldaac_requests_ncss_ds1225_samedata_csv.json",
        "ornldaac_requests_ncss_ds1225_samedata_netcdf.json",
        "podaac_requests_ncss_samedata_netcdf.json",
        "podaac_requests_ncss_samedata_csv.json",
    ]

    # load file containing the list of download URLs, destination filenames, and layers
    current_dir = os.path.dirname(__file__)

    for base_file in base_files:

        LOGGER.info(f"start {base_file}")
        filepath = os.path.join(current_dir, base_file)

        with open(filepath, mode="r") as json_file:
            download_files = json.load(json_file)

        # set the desired concurrency level
        concurrency_level = 1

        LOGGER.info(f"Concurrency level is {concurrency_level}")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            download_base_files(
                loop,
                current_dir,
                download_files,
                my_base_validator,
                concurrency_level,
                LOGGER,
            )
        )

        LOGGER.info(f"finish {base_file}")

    end_time = datetime.datetime.now()

    LOGGER.info("Ended at " + end_time.strftime("%Y-%m-%d %H:%M:%S"))
    LOGGER.info("Elapsed time " + str(end_time - start_time))
