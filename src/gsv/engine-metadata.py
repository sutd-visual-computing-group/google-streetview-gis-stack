# -*- coding: utf-8 -*-

# Import base libraries
import os, time, random, math

# Import numerical computing libraries
import pandas as pd
import numpy as np

# Import async libraries
import asyncio, aiohttp

# Import other libraries
from tqdm import tqdm

# Import project dependencies
import utils


class MetaData:
    """
    This class implements attributes and functions to extract Google Street View Metadata using extracted points
    """
    def __init__(self, csv_file, api_key, secret_key, save_dir, api_limit=500, filter_identifier=None, size="200x200", fov=120, heading=0):
        """
        Initialize the GSV metadata downloader object

        Args:
            csv_file    : csv_file containing extracted points
            api_key     : Google Street View Static API key (Please store this secretly)
            secret_key  : Google Street View Static API secret key (Please store this secretly)
            save_dir    : directory to save the extracted data
            api_limit   : Google Street View Static API Limit per second (Default = 500 per sec)
            filter_identifier   : Filter value
            size        : GSV API image size (default = 200x200)
            fov         : GSV API field of view (default = 120)
            heading     : GSV API heading value (default = 0)

        Returns:
            None
        """
        self.df = pd.read_csv(csv_file).reset_index(drop=True)
        self.df = self.df.dropna()
        self.df = self.df.astype({"x": float, "y": float, "kml": int})
        self.df = self.df.rename(columns={"x":"lng", "y": "lat"})
        self.df = self.df[["lat", "lng", "kml"]]
        
        if filter_identifier:
            self.df = self.df[self.df['kml'] == filter_identifier]

        self.api_key = api_key
        self.api_limit = api_limit
        self.secret_key = secret_key
        self.filter_identifier = filter_identifier
        self.parent_url = r"https://maps.googleapis.com/maps/api/streetview"
        self.base_param_url = r"?size={}&fov={}&heading={}&location=".format(size, fov, heading)
        self.output_file = os.path.join(save_dir, "extracted_points-{}-with-metadata-using-requests-async.csv".format(filter_identifier))
        self.run_status = True

        if os.path.exists(self.output_file):
            self.run_status = False
            

    async def _meta_url_parse(self, meta_url, session):
        """
        Asynchronous function to download GSV metadata

        Args:
            meta_url    : URL
            session     : TCP Session object

        Returns:
            tuple (retrieved_latitude, retrieved_longitude, pano_id, status)
        """
        try:
            async with session.get(meta_url) as response:
                metadata = await response.json()
                if metadata['status'] == "OK":
                    return metadata['location']['lat'], metadata['location']['lng'], metadata['pano_id'], metadata['status']
                elif metadata['status'] == "ZERO_RESULTS":
                    return -1, -1, -1, metadata['status']
                else:
                    return 0, 0, 0, metadata['status']
        except Exception as ex:
            return 0, 0, 0, "{}_retrieve_again".format(ex)


    async def _bound_fetch(self, sem, url, session):
        """
        Asynchronous function to call GSV metadata API

        Args:
            sem     : Semaphore
            url     : URL
            Session : TCP Session object
        """
        async with sem:
            return await self._meta_url_parse(url, session)


    async def _download_all_metadata(self, df_chunk):
        """
        Asynchronous function to download all metadata

        Args:
            df_chunk    : pandas dataframe
        """
        tasks = []
        sem = asyncio.Semaphore(1000)

        async with aiohttp.ClientSession() as session:
            for i in df_chunk.index:
                lat, lng = df_chunk.loc[i, 'lat'], df_chunk.loc[i, 'lng']
                meta_url = "{}/metadata{}{},{}&key={}&callback=initMap".format(self.parent_url, self.base_param_url, str(lat), str(lng), self.api_key)
                signed_meta_url = utils.sign_url(meta_url, self.secret_key)

                task = asyncio.ensure_future(self._bound_fetch(sem, signed_meta_url, session))
                tasks.append(task)

            responses = asyncio.gather(*tasks)
            return await responses

    
    def _break_into_chunks(self, df):
        """
        Break dataframe into chunks based on API limit

        Args:
            df  : pandas dataframe
        """
        nrows = df.shape[0]
        chunk_size = min(nrows, self.api_limit - 1)
        chunks = [df.loc[df.index[i:i + chunk_size]].copy() for i in range(0, nrows, chunk_size)]
        return chunks

    
    def get_run_status(self):
        return self.run_status


    def run_tasks(self, verbose=False):
        """
        Interfacing function to download all metadata

        Args:
            verbose : If true, output will be printed
        """
        print('> Running task for district {}'.format(self.filter_identifier))
        chunks = self._break_into_chunks(self.df)
        dfs = []

        for chunk_index in tqdm(range(len(chunks))):
            timer = time.time()
            is_last_chunk = chunk_index + 1 == len(chunks)
            df = chunks[chunk_index]
            loop = asyncio.get_event_loop()
            future = asyncio.ensure_future(self._download_all_metadata(df))
            result = loop.run_until_complete(future)

            df['processed'] = result
            df[['ret_lat', 'ret_lng', 'pano_id', 'status']] = pd.DataFrame(df['processed'].tolist(), index=df.index)
            del df['processed'] 
            dfs.append(df)
            
            delta = time.time() - timer
            if delta <= 1 and is_last_chunk==False:
                #print("> Waiting for {} sec due to API limits".format(delta))
                time.sleep(1.0 - delta)

        final_df = pd.concat(dfs)
        final_df.to_csv(self.output_file, index=None)
        
        if verbose:
            print(final_df.head(10))
        

    def retry_error_points(self, verbose=False):
        """
        Interfacing function to download all failed metadata points

        Args:
            verbose : If true, output will be printed
        """
        print('> Retrying failed points for district {}'.format(self.filter_identifier))
        while True:
            df_primary = pd.read_csv(self.output_file).reset_index(drop=True)
            error_df = df_primary[df_primary['pano_id'] == "0"]

            if error_df.shape[0] == 0:
                break
            
            chunks = self._break_into_chunks(error_df)
            dfs = []

            for chunk_index in tqdm(range(len(chunks))):
                timer = time.time()
                is_last_chunk = chunk_index + 1 == len(chunks)
                df = chunks[chunk_index]
                loop = asyncio.get_event_loop()
                future = asyncio.ensure_future(self._download_all_metadata(df))
                result = loop.run_until_complete(future)

                df['processed'] = result
                df[['ret_lat', 'ret_lng', 'pano_id', 'status']] = pd.DataFrame(df['processed'].tolist(), index=df.index)
                del df['processed'] 
                dfs.append(df)
                
                delta = time.time() - timer
                if delta <= 1 and is_last_chunk==False:
                    #print("> Waiting for {} sec due to API limits".format(delta))
                    time.sleep(1.0 - delta)

            
            error_final_df = pd.concat(dfs)
            df_primary.update(error_final_df)
            df_primary.to_csv(self.output_file, index=None)

            if verbose:
                print(df_primary.head(10))
            


    def print_statistics(self):
        """
        Print statistics of output file
        """
        df = pd.read_csv(self.output_file).reset_index(drop=True)
        df_ok = df[df['status'] == "OK"]
        print("> Printing Final Statistics of retrieved metadata")
        print("> Number of total points = {}".format(df.shape[0]))
        print("> Number of points with GSV data = {}".format(df[df['status'] == "OK"].shape[0]))
        print("> Number of points with ZERO results = {}".format(df[df['status'] == "ZERO_RESULTS"].shape[0]))
        print("> Number of points with URL errors = {}".format(df[df['pano_id'] == "0"].shape[0]))
        print("> Number of unique panoroma ids = {}".format(df_ok['pano_id'].nunique()))
    


if __name__ == "__main__":
    project_path = '/projects/foto-kompass/'
    target_csv = os.path.join(project_path, 'data', 'singapore', 'extracted_points.csv')
    save_dir = os.path.join(project_path, 'data', 'singapore', 'gsv_metadata')
    district_list = pd.read_csv(target_csv).reset_index(drop=True).dropna().kml.unique().astype(np.int16)
    #print(type(district_list), len(district_list))

    env = utils.GET_API_AND_SECRET_KEY(os.path.join(project_path, "project-env.json"))
    #print(env)

    for district in district_list:
        start = time.time()
        metadata_instance = MetaData(target_csv, 
                                    api_key=env['API_KEY'],
                                    secret_key=env['SECRET_KEY'],
                                    save_dir=save_dir,
                                    filter_identifier=district)

        if metadata_instance.get_run_status():
            metadata_instance.run_tasks()
            metadata_instance.retry_error_points()
            metadata_instance.print_statistics()
        else:
            print("> Target csv file for district {} already exists. Skipping...".format(district))

        print("> The process took {} sec".format(time.time() - start))
        print("------------------------------------------------------")
