import re
import discogs_client
import pandas as pd

from services.config import DISCOGS_TOKEN

def get_discogs_collection(on_progress=None) -> pd.DataFrame:
    d = discogs_client.Client('D-Vella@github', user_token=DISCOGS_TOKEN)
    me = d.identity()

    df = pd.DataFrame({'Artist': pd.Series(dtype='str'),
                       'Title': pd.Series(dtype='str'),
                       'PressingYear': pd.Series(dtype='int'),
                       'DateAdded': pd.Series(dtype='datetime64[ns]'),
                       'Format': pd.Series(dtype='str'),
                       'ReleaseID': pd.Series(dtype='int'),
                       'ReleaseMasterID': pd.Series(dtype='int'),
                       'ReleaseYear': pd.Series(dtype='int'),
                       'ReleaseDesc': pd.Series(dtype='str')})

    total_items = len(me.collection_folders[0].releases) # type: ignore

    for i, item in enumerate(me.collection_folders[0].releases):
        if on_progress:
            on_progress(int((i + 1) / total_items * 100), f"Processing item {i + 1} of {total_items}")

        #seperate logic for items that need cleaning:
        ReleaseFormat = item.release.formats[0]
        ReleaseDesc = f"{ReleaseFormat['qty']} x {ReleaseFormat['name']} ({', '.join(ReleaseFormat['descriptions'])})"
        ReleaseMaster = item.release.master
        if ReleaseMaster:
            ReleaseYear = ReleaseMaster.year
            ReleaseMasterID = ReleaseMaster.id
        else:
            ReleaseYear = None
            ReleaseMasterID = f'M{item.release.id}'

        df.loc[len(df)] = {'Artist': re.sub(r'\s*\(\d+\)$', '', item.release.artists[0].name),
                        'Title': item.release.title,
                        'PressingYear': item.release.year if item.release.year != 0 else None,
                        'ReleaseYear': ReleaseYear,
                        'DateAdded': str(item.date_added)[0:10], #Just want the date.
                        'Format': item.release.formats[0]['name'],
                        'ReleaseID': item.release.id,
                        'ReleaseMasterID': ReleaseMasterID,
                        'ReleaseDesc': ReleaseDesc
    }

    df = df.sort_values(by=['DateAdded'], ascending=False).reset_index(drop=True)
    return df