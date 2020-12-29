# Google Streetview Geographic Information System (GIS) stack
To help visual geo-localization research, this tool helps to generate Google Street View coverage maps by leveraging on Geographic Information System (using GIS packages in R) and Google Static Street View API (using Python). This code has been tested with Singapore. Do note that this tool is not intended for production environments and is strictly for use within the SUTD Visual Computing Group.



## Problem Statement

Google provides extensive street view coverage in Singapore. To obtain accurate coverage details, we need to query the Google Static StreetView API for the presence of StreetView panorama at multiple geo-locations. A naive way of doing this would be to follow a brute force form of approach querying every possible latitude and longitude spaced at regular intervals to obtain the coverage. Since this is costly and inefficient, we have designed a pipeline to obtain coverage details much more efficiently with no API usage cost.



## Pipeline

### Geographic Information System (GIS)

The GIS stack performs the following operations to sample unique geo-locations at 1m interval throughout all the roads/ streets in Singapore using Open Street Maps API.

1. Create base map of Singapore (from shapefile).
2. Import any administrative unit/ geographic unit districts information as vector file. (We use KML format)
3. Create osm (Open street maps) query and retrieve osm data
4. Do geometric operations to find the intersection with base map and perform union of all the resulting regions
5. Now sample points at 1m distance at regular intervals to create extracted_points.csv. 



### Google Static StreetView (GSV) API

Now in this section, we will use the extracted points from the GIS stack to query the Google Static StreetView metadata API to check the presence of Google StreetView panorama image. In order to perform a query, we require specific spatial location parameters (Latitude/ Longitude or Plus codes). In the GIS stack, for every sampled point, we extract the corresponding latitude and longitude data.

Google associates every StreetView panorama using a unique id called pano_id. Using the metadata API service, we extract all the required information to create the coverage statistics and maps. Every geo-location query will return the following details:

| Field             | Details                                                      |
| ----------------- | ------------------------------------------------------------ |
| lat/ lng          | latitude and longitude extracted from the GIS stack          |
| kml               | district/ administrative unit                                |
| ret_lat/  ret_lng | latitude and longitude returned by GSV metadata service. (In many occasions this may slightly differ from the query as Google returns the best match for the query) |
| pano_id           | Unique panorama id for the specific geo-location             |
| status            | The status of query returned by Google. (OK, ZERO_RESULTS, OVER_QUERY_LIMIT). If status=ZERO_RESULTS, pano_id is recorded as -1. If OVER_QUERY_LIMIT, we repeat the queries again. |



A sample retrieved record is shown below.

| lat              | lng              | kml  | ret_lat          | ret_lng          | pano_id                | status |
| ---------------- | ---------------- | ---- | ---------------- | ---------------- | ---------------------- | ------ |
| 1.36597564133697 | 103.890522755108 | 1    | 1.36598953663481 | 103.890562223944 | 1aZIE3M2YwiDkzIXdo1Q1Q | OK     |



## How to use the code?





## Coverage and GSV meta-data statistics

## Singapore Coverage Map

![](./assets/Rplot.png)



## Acknowledgements

This work was done by Keshigeyan Chandrasegaran (Information Systems Design and Technology) during his time at [Temasek Laboratories, Singapore University of Technology and Design](https://temasek-labs.sutd.edu.sg/). Please contact him at keshigeyan@sutd.edu.sg regarding any further questions. 



## References

