import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go

class BearableData:

    """This is a basic ETL process wrapped up in a class.
    This allows one to examine the data created in various stages of the process."""
    def __init__(self, bearable_file):
        self.bearable_file = bearable_file
        self.STA_df = self.extract_data(self.bearable_file)
        self.factors_unique = ''
        self.categories = ['Symptom', 'Mood', 'Energy', 'Sleep', 'Sleep quality', 'Factors']
        self.INT_df = self.wrangle(self.STA_df)
        
        self.REP_dates = pd.DataFrame(self.STA_df['date'].unique(), columns=['date'])
        self.REP_longform = self.build_longform(self.INT_df, self.categories)
        
    def wrangle(self, df):
        # Timestamps are a mess in bearable export data. (It's true, sorry guys and gals.)
        # We have to convert all data to usable timestamps before we can report anything.
        mask = df['time of day'].isna() # find missing data
        df.loc[mask, 'time of day'] = '00:00' # fill in 00:00 for missing data
        df['time of day'] = df.apply(lambda x: self.get_time(x['time of day']), axis=1)
        timedelta = pd.to_timedelta(df['time of day'] + ':00') # add seconds
        df['datetime'] = df['date'] + timedelta # create timestamp from date and time

        return df

    def extract_data(self, file):
        df = pd.read_csv(file)
        df.loc[:, 'date'] = pd.to_datetime(df.loc[:, 'date'])

        return df

    def get_time(self, key):
        # the data contains strings vaguely pointing to periods. 
        # we have to convert these to hours and minutes for wrangle().
        if isinstance(key, str):
            if ':' in key:
                return key
        if not key:
            return '00:00'
        return {
            'pre': '00:00',
            'am': '06:00',
            'mid': '12:00',
            'pm': '18:00',
            'all day' : '00:00',
            }.get(key)

    def get_factors_unique(self, df_category):
            # get unique factors from data and store in a set
            all_factors = df_category.detail + str(' | ')
            all_factors = all_factors.sum().split(' | ')
            factors_unique = set(all_factors)
            factors_unique.remove('')
            factors_unique = sorted(factors_unique)
            
            return factors_unique

    def build_longform(self, df, categories):
        df_longform = pd.DataFrame()
        for category in categories:
            df_category = df.loc[(df['category'] == category)]

            # hours of sleep need to be converted to floating point.
            if category == 'Sleep':             
                df_category['rating/amount'] = df_category['rating/amount'] + ":0"
                # TODO: don't use apply for this.
                df_category['rating/amount'] = df_category.apply(lambda x: pd.to_timedelta(x['rating/amount']), axis=1)
                df_category['rating/amount'] = df_category['rating/amount'] / datetime.timedelta(minutes=1) / 60
            
            # always convert to float for rating/amount
            df_category['rating/amount'] = pd.to_numeric(df_category.loc[:, 'rating/amount'], downcast='float')

            # symptoms are averaged and aggregated to daily levels. 
            # TODO: retain different symptoms and create reporting option for this.
            # To do this, remove one sequence of .groupby() from the last line.
            if category == 'Symptom':
                df_category['detail'] = df_category['detail'].str.extract(r'(.*(?=\ \())')
                df_category = df_category.groupby(['datetime', 'category', 'detail']).agg('mean').reset_index().groupby(['datetime', 'category']).agg('sum').reset_index()

            if category == 'Factors':
                # find factors in dataframe and set a numeric value
                # we use this to aggregate values and create a barchart
                df_factors = pd.DataFrame()
                self.factors_unique = self.get_factors_unique(df_category)
                for factor in self.factors_unique:
                    mask = df_category[(df_category['detail'].str.contains(factor))]
                    mask['factor'] = factor
                    mask['rating/amount'] = 1
                    mask = mask[['datetime', 'category', 'factor', 'rating/amount']]
                    df_factors = df_factors.append(mask)
                df_category = df_factors

            # create rolling average column
            window = 7 # how many values to average?
            df_category['average'] = df_category['rating/amount'].rolling(window).mean().round(2)
            df_longform = df_longform.append(df_category)

        df_longform = df_longform[['datetime', 'category', 'factor', 'rating/amount', 'average', 'detail']]
        df_longform.sort_values(by='datetime', inplace=True)
        return df_longform

def draw_bearable_fig(data):
    fig_measurements = go.Figure()
    colors = ['#00429d', '#4b568d', '#6c6a7a', '#ff0000', '#fdd249', '#ffa563', '#e06dff']

    for category in data.categories:
        selection = data.REP_longform.loc[(data.REP_longform['category'] == category)]

        if category == 'Factors':
            fig_factors = go.Figure()
            for factor in data.factors_unique:
                df_factor = selection.loc[selection['factor'] == factor]
                fig_factors.add_trace(go.Histogram(x=df_factor['datetime'], y=df_factor['rating/amount'], name = factor, histfunc='sum', xbins=dict(size= '604800000'), autobinx=False) # 1 week in milliseconds
                )
        
        else:
            trace_name_avg = f'{category} average'
            fig_measurements.add_trace(go.Scatter(x=selection['datetime'], y=selection['rating/amount'], name=category, showlegend=True, line_shape='spline', fill='tozeroy'))
            fig_measurements.add_trace(go.Scatter(x=selection['datetime'], y=selection['average'], name=trace_name_avg, showlegend=True, line_shape='spline', fill='tozeroy'))


    fig_measurements.update_layout(
        # width=900,
        # height=400,
        autosize=True,
        margin=dict(t=40, b=10, l=10, r=10),
        template="plotly",
        # barmode='overlay'
        )
    fig_measurements.update_xaxes(
    rangeslider_visible = True
    )

    return fig_measurements, fig_factors

if __name__ == "__main__":
    print("Pawprint is a module to be imported by a script.")