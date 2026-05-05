import plotly.express as px
from .config import CITY_COORDS
import pandas as pd


def add_coords(df, city_col='city'):
    # create lat/lon columns from city Chinese name
    df = df.copy()
    def _lon(c):
        v = CITY_COORDS.get(c)
        return v[0] if v else None
    def _lat(c):
        v = CITY_COORDS.get(c)
        return v[1] if v else None
    df['lon'] = df[city_col].apply(_lon)
    df['lat'] = df[city_col].apply(_lat)
    return df




def plot_map_plotly(df):
    dfp = add_coords(df, city_col='city')
    dfp = dfp.dropna(subset=['lon','lat'])
    if dfp.empty:
        return None
    fig = px.scatter_mapbox(
    dfp,
        lat='lat', lon='lon', size='aqi', color='aqi',
        hover_name='city', hover_data=['pm25','pm10','update_time'],
        size_max=30, zoom=3)
    fig.update_layout(mapbox_style='carto-positron', margin={'t':0,'b':0,'l':0,'r':0})
    return fig