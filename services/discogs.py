import re
import discogs_client
import pandas as pd

from services.config import DISCOGS_TOKEN

def get_discogs_collection() -> pd.DataFrame:
    d = discogs_client.Client('D-Vella@github', user_token=DISCOGS_TOKEN)
    me = d.identity()

    df = pd.DataFrame({'Artist': pd.Series(dtype='str'),
                       'Title': pd.Series(dtype='str'),
                       'PressingYear': pd.Series(dtype='int'),
                       'DateAdded': pd.Series(dtype='datetime64[ns]'),
                       'Format': pd.Series(dtype='str'),
                       'ReleaseID': pd.Series(dtype='int'),
                       'ReleaseMasterID': pd.Series(dtype='int')})

    for item in me.collection_folders[0].releases:
        df.loc[len(df)] = {'Artist': re.sub(r'\s*\(\d+\)$', '', item.release.artists[0].name),
                        'Title': item.release.title,
                        'PressingYear': item.release.year if item.release.year != 0 else None,
                        'DateAdded': str(item.date_added)[0:10], #Just want the date.
                        'Format': item.release.formats[0]['name'],
                        'ReleaseID': item.release.id,
                        'ReleaseMasterID': item.release.master.id if item.release.master else None,
    }

    df = df.sort_values(by=['DateAdded'], ascending=False).reset_index(drop=True)
    return df