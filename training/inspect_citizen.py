"""Inspect the official remote archive without downloading all videos."""
from remotezip import RemoteZip
URL='https://download.microsoft.com/download/b/8/8/b88c0bae-e6c1-43e1-8726-98cf5af36ca4/ASL_Citizen.zip'
if __name__ == '__main__':
    with RemoteZip(URL) as archive:
        names=archive.namelist()
        print('Members:',len(names),flush=True)
        print('\n'.join(names[:15]),flush=True)
        for name in names:
            if name.lower().endswith(('.csv','.txt','.pdf')):
                print(name, archive.getinfo(name).file_size,flush=True)
