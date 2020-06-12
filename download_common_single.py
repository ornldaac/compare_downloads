import asyncio
import datetime
import hashlib
import json
import logging
import os
import subprocess
import sys
from functools import partial
from shutil import copyfile

import aiohttp
import netCDF4
import requests
from aiohttp import http_exceptions, web

run_date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def store_error(basefilepath, testfilepath, LOGGER):
    error_dir = f"./error/{run_date}/"
    destination = os.path.join(error_dir, os.path.dirname(basefilepath))
    os.makedirs(destination, exist_ok=True)
    LOGGER.error(f"    storing errors in {destination}\n")

    copyfile(basefilepath, error_dir + basefilepath)
    copyfile(testfilepath, error_dir + testfilepath)

    if basefilepath.endswith(".nc"):
        copyfile(basefilepath + ".txt", error_dir + basefilepath + ".txt")
        copyfile(testfilepath + ".txt", error_dir + testfilepath + ".txt")
    return


def md5Checksum(filePath):
    with open(filePath, "rb") as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()


def my_base_validator(url, basefilepath, testfilepath, LOGGER):
    if basefilepath.endswith(".nc"):
        netcdf_base_validator(url, basefilepath, testfilepath, LOGGER)
    else:
        csv_base_validator(url, basefilepath, testfilepath, LOGGER)


def my_test_validator(url, basefilepath, testfilepath, LOGGER):
    if basefilepath.endswith(".nc"):
        netcdf_test_validator(url, basefilepath, testfilepath, LOGGER)
    else:
        csv_test_validator(url, basefilepath, testfilepath, LOGGER)


def csv_base_validator(url, basefilepath, testfilepath, LOGGER):
    checksum = md5Checksum(basefilepath)
    LOGGER.debug(f"the md5 checksum of {basefilepath} is {checksum}\n")


def netcdf_base_validator(url, basefilepath, testfilepath, LOGGER):
    with netCDF4.Dataset(basefilepath, mode="r") as ds:
        # make sure all expected layers contain data
        for key, variable in ds.variables.items():
            if len(variable.shape) > 0 and variable.shape[0] == 0:
                raise RuntimeError(
                    f"Variable {key} in {basefilepath} does not contain any data, try downloading again"
                )
        filepath = basefilepath + ".txt"
        with open(filepath, "wb") as f:
            cmd = f"ncdump {basefilepath}"
            text = subprocess.check_output(cmd, shell=True)
            f.write(text)
    checksum = md5Checksum(basefilepath)
    LOGGER.debug(f"the md5 checksum of {basefilepath} is {checksum}\n")


def csv_test_validator(url, basefilepath, testfilepath, LOGGER):
    checksumbase = md5Checksum(basefilepath)
    checksumtest = md5Checksum(testfilepath)
    if checksumbase != checksumtest:
        LOGGER.error(
            f"checksums ne {basefilepath} {checksumbase}\n"
            + f"             {testfilepath} {checksumtest}\n"
        )
        store_error(basefilepath, testfilepath, LOGGER)
    else:
        LOGGER.info(
            f"the md5 checksum of {testfilepath} {checksumtest} matches base {checksumbase} \n"
        )


def netcdf_test_validator(url, basefilepath, testfilepath, LOGGER):
    with netCDF4.Dataset(testfilepath, mode="r") as ds:
        # make sure all expected layers contain data
        for key, variable in ds.variables.items():
            if len(variable.shape) > 0 and variable.shape[0] == 0:
                raise RuntimeError(
                    f"Variable {key} in {testfilepath} does not contain any data, try downloading again"
                )
        filepath = testfilepath + ".txt"
        with open(filepath, "wb") as f:
            cmd = f"ncdump {testfilepath}"
            text = subprocess.check_output(cmd, shell=True)
            f.write(text)
    checksumbase = md5Checksum(basefilepath)
    checksumtest = md5Checksum(testfilepath)
    if checksumbase != checksumtest:
        LOGGER.error(
            f"checksums ne {basefilepath} {checksumbase}\n"
            + f"             {testfilepath} {checksumtest}\n"
        )
        store_error(basefilepath, testfilepath, LOGGER)
    else:
        LOGGER.info(
            f"the md5 checksum of {testfilepath} {checksumtest} matches base {checksumbase} \n"
        )


def _download_file(url, filepath, validator, LOGGER):
    try:
        with requests.get(url) as response:
            LOGGER.debug("downloading {0} ... {1} ...".format(url, filepath))
            with open(filepath, "wb") as f:
                if response.status_code == 200:
                    # save file
                    chunk = response.content
                    f.write(chunk)
                elif response.status_code == 404:
                    LOGGER.debug("error downloading {0} ... {1} ".format(url, filepath))
                    raise web.HTTPNotFound()
                else:
                    LOGGER.debug("error downloading {0} ... {1} ".format(url, filepath))
                    raise http_exceptions.HttpProcessingError(
                        code=response.status_code,
                        message=response.reason,
                        headers=response.headers,
                    )

        LOGGER.debug("validating {0} ...".format(filepath))
        if validator is not None:
            validator()

        LOGGER.debug("download done {0}".format(url))
        return filepath, (response.status_code, tuple(response.headers.items()))

    except Exception as e:
        LOGGER.debug("error downloading {0} ... {1} ".format(url, filepath))
        raise e


def download_base_files(current_dir, files, validator, LOGGER):
    # create any destination directories that don't already exist
    for file in files:
        destination_dir = os.path.join(current_dir, os.path.dirname(file[1]))
        os.makedirs(destination_dir, exist_ok=True)

        _download_file(
            file[0], file[1], partial(validator, *file, LOGGER), LOGGER,
        )

    LOGGER.debug("downloaded {0:,} files...".format(len(files)))


def download_test_files(current_dir, files, validator, LOGGER):
    # create any destination directories that don't already exist
    for file in files:
        destination_dir = os.path.join(current_dir, os.path.dirname(file[1]))
        os.makedirs(destination_dir, exist_ok=True)

        _download_file(
            file[0], file[2], partial(validator, *file, LOGGER), LOGGER,
        )

    LOGGER.debug("downloaded {0:,} files...".format(len(files)))


async def _download_file_nonstream(
    url, filepath, session, loop, validator, semaphore, LOGGER
):
    try:
        async with semaphore, await session.get(
            url, timeout=600, ssl=False
        ) as response:
            LOGGER.debug("downloading {0} ... {1} ...".format(url, filepath))
            with open(filepath, "wb") as f:
                if response.status == 200:
                    # save file
                    data = await response.read()
                    if data:
                        f.write(data)
                elif response.status == 404:
                    LOGGER.debug("error downloading {0} ... {1} ".format(url, filepath))
                    raise web.HTTPNotFound()
                else:
                    LOGGER.debug("error downloading {0} ... {1} ".format(url, filepath))
                    raise http_exceptions.HttpProcessingError(
                        code=response.status,
                        message=response.reason,
                        headers=response.headers,
                    )

        LOGGER.debug("validating {0} ...".format(filepath))
        if validator is not None:
            validator()

        LOGGER.debug("download done {0}".format(url))
        return filepath, (response.status, tuple(response.headers.items()))

    except asyncio.TimeoutError as e:
        LOGGER.error("request timed out: {0}".format(url))
        raise e
    except Exception as e:
        if not loop.is_closed():
            LOGGER.debug("error downloading {0} ... {1} ".format(url, filepath))
            raise e


async def download_base_files_nonstream(
    loop, current_dir, files, validator, concurrency_level, LOGGER
):
    # create any destination directories that don't already exist
    for file in files:
        destination_dir = os.path.join(current_dir, os.path.dirname(file[1]))
        os.makedirs(destination_dir, exist_ok=True)

    async with aiohttp.ClientSession(loop=loop) as session:
        # create a semaphore to throttle the number of concurrent downloads
        semaphore = asyncio.Semaphore(concurrency_level, loop=loop)
        # create a generator to return all of the calls to _download_file_nonstream
        download_tasks = (
            _download_file_nonstream(
                f[0],
                f[1],
                session,
                loop,
                partial(validator, *f, LOGGER),
                semaphore,
                LOGGER,
            )
            for f in files
        )
        # process the download tasks until complete or until one or more of the request exhausts all retries
        LOGGER.debug("downloading {0:,} files...".format(len(files)))
        await asyncio.gather(*download_tasks, loop=loop)


async def download_test_files_nonstream(
    loop, current_dir, files, validator, concurrency_level, LOGGER
):
    # create any destination directories that don't already exist
    for file in files:
        destination_dir = os.path.join(current_dir, os.path.dirname(file[1]))
        os.makedirs(destination_dir, exist_ok=True)

    async with aiohttp.ClientSession(loop=loop) as session:
        # create a semaphore to throttle the number of concurrent downloads
        semaphore = asyncio.Semaphore(concurrency_level, loop=loop)
        # create a generator to return all of the calls to _download_file_nonstream
        download_tasks = (
            _download_file_nonstream(
                f[0],
                f[2],
                session,
                loop,
                partial(validator, *f, LOGGER),
                semaphore,
                LOGGER,
            )
            for f in files
        )
        # process the download tasks until complete or until one or more of the request exhausts all retries
        LOGGER.debug("downloading {0:,} files...".format(len(files)))
        await asyncio.gather(*download_tasks, loop=loop)
