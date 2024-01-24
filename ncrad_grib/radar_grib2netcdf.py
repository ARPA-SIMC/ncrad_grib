#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Trasforma i grib2 contenenti la precipitazione cumulata da radar
in file netcdf (attualmente nel formato leggibile dalle routine
IDL)

Da modificare:
- gestione della variabile time perchè il netcdf sia convenzionale
- gestione delle cumulate in minuti

"""

import numpy as np
import argparse
import netCDF4

from datetime import datetime
from eccodes import codes_grib_new_from_file, codes_get_values, codes_get, codes_release

import warnings

warnings.filterwarnings("ignore")

# COSTANTI
rmiss_netcdf = "   -0.0100000"  # default dei netcdf
rmiss_grib = 9999


def get_args():
    parser = argparse.ArgumentParser(
        description="Programma per la conversione dei file grib2 di cumulate radar in netcdf.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-i",
        "--input_file",
        dest="inputfile",
        required=True,
        help="File di input, required",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        dest="outputfile",
        required=False,
        help="File di output, optional",
    )

    args = parser.parse_args()

    return args


def radar_grib2netcdf(name_grib, name_nc=""):

    try:
        grib_file = open(name_grib, "rb")

        gid = codes_grib_new_from_file(grib_file)

        # Data di inizio cumulata
        # grib_date = str(codes_get(gid, "dataDate"))
        # grib_time = str(codes_get(gid, "dataTime")).zfill(4)

        grib_year_end = str(codes_get(gid, "yearOfEndOfOverallTimeInterval")).zfill(4)
        grib_month_end = str(codes_get(gid, "monthOfEndOfOverallTimeInterval")).zfill(2)
        grib_day_end = str(codes_get(gid, "dayOfEndOfOverallTimeInterval")).zfill(2)
        grib_hour_end = str(codes_get(gid, "hourOfEndOfOverallTimeInterval")).zfill(2)
        grib_min_end = str(codes_get(gid, "minuteOfEndOfOverallTimeInterval")).zfill(2)
        date_end_cum = datetime.strptime(
            "{}{}{}{}{}".format(
                grib_year_end, grib_month_end, grib_day_end, grib_hour_end, grib_min_end
            ),
            "%Y%m%d%H%M",
        )
        unit_cum = codes_get(gid, "indicatorOfUnitOfTimeRange")

        if name_nc is None or name_nc == "":
            name_nc = ".".join(name_grib.split("/")[-1].split(".")[:-1]) + ".nc"

        # Apertura del file netcdf
        ncid = netCDF4.Dataset(name_nc, "w", format="NETCDF4")

        ncid.createDimension("time", None)
        ncid.createDimension("lat", codes_get(gid, "Nj"))
        ncid.createDimension("lon", codes_get(gid, "Ni"))
        ncid.createDimension("geo_dim", 4)
        ncid.createDimension("mesh_dim", 2)

        v = ncid.createVariable("lon", "f4", ("lon",))
        v.long_name = "longitude"
        v.units = "degrees_east"
        v.standard_name = "longitude"
        a = codes_get(gid, "longitudeOfFirstGridPointInDegrees")
        b = codes_get(gid, "longitudeOfLastGridPointInDegrees")
        mesh_lon = (b - a) / (codes_get(gid, "Ni") - 1)
        v[:] = np.append(
            np.array(np.arange(a, b, (b - a) / (codes_get(gid, "Ni") - 1))), b
        )

        v = ncid.createVariable("lat", "f4", ("lat",))
        v.long_name = "latitude"
        v.units = "degrees_north"
        v.standard_name = "latitude"
        a = codes_get(gid, "latitudeOfLastGridPointInDegrees")
        b = codes_get(gid, "latitudeOfFirstGridPointInDegrees")
        mesh_lat = (b - a) / (codes_get(gid, "Nj") - 1)
        v[:] = np.append(
            np.array(np.arange(a, b, (b - a) / (codes_get(gid, "Nj") - 1))), b
        )

        # Nella conversione da griba netcdf usiamo la
        # definizione di "time" convenzionale
        v = ncid.createVariable("time", "f4", ("time",))
        v.long_name = "time"
        if unit_cum == 1:
            v.units = "hours since 1970-01-01 00:00:0"
        elif unit_cum == 0:
            v.units = "minutes since 1970-01-01 00:00:0"
        v.calendar = "gregorian"
        v[:] = np.array([netCDF4.date2num(date_end_cum, units=v.units,
                                          calendar = "gregorian")])

        v = ncid.createVariable("geo_dim", "f4", ("geo_dim",))
        v.long_name = "Geo limits [xLL, xUR, yLL, yUR]"
        v.units = "degrees"
        # La scrittura dei limiti è convenzionale rispetto alla versione
        # CF-1.8 (valori crescenti)
        v[:] = np.array(
            [
                codes_get(gid, "longitudeOfFirstGridPointInDegrees"),
                codes_get(gid, "longitudeOfLastGridPointInDegrees"),
                codes_get(gid, "latitudeOfLastGridPointInDegrees"),
                codes_get(gid, "latitudeOfFirstGridPointInDegrees"),
            ]
        )

        v = ncid.createVariable("mesh_dim", "f4", ("mesh_dim",))
        v.long_name = "Grid Mesh Size [X_mesh_size, Y_mesh_size]"
        v.units = "degrees"
        v[:] = np.array([mesh_lon, mesh_lat])

        v = ncid.createVariable(
            "cum_pr_mm",
            "f4",
            (
                "time",
                "lat",
                "lon",
            ),
        )
        v.long_name = "Radar Precipitation amount"
        v.units = "kg m-2"
        v.standard_name = "precipitation_amount"
        v.valid_min = 0.0
        v.valid_max = 10000.0
        v.coordinates = "lat lon"
        v.detection_minimum = "      0.00000"
        v.undetectable = "      0.00000"
        v.var_missing = rmiss_netcdf
        v.accum_time_h = float(codes_get(gid, "lengthOfTimeRange"))
        # Necessario convertire in arraymultidim, uso il numero di valori della lon(Ni) e poi inverto sul primo asse
        data = np.array(codes_get_values(gid))
        data = np.where(
            data != codes_get(gid, "missingValue"), data, rmiss_netcdf
        )  # replace missingvalue
        v[:] = np.array([np.flip(np.reshape(data, (-1, codes_get(gid, "Ni"))), 0)])

        # ATTIBUTI GLOBALI
        ncid.Conventions = "CF-1.8"
        ncid.history = "Created by radar_grib2netcdf"
        ncid.institute = "Arpae Emilia-Romagna - SIMC"
        ncid.title = "Radar product"
        ncid.reference = "palberoni@arpae.it"
        ncid.comment = "none"
        ncid.MapType = "SRT"

        ncid.close()

        codes_release(gid)
        grib_file.close()

    except OSError:
        print("Cannot open {}".format(name_grib))
        print("Probabile file mancante.")


def main():
    args = get_args()

    inputfile = args.inputfile
    if args.outputfile:
        outputfile = args.outputfile
    else:
        outputfile = None

    radar_grib2netcdf(inputfile, outputfile)


if __name__ == "__main__":
    main()
