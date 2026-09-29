"""Retrieve only the official atlas_20 records (about 5 MB, not 1 GB)."""
import concurrent.futures, html, io, pathlib, re, struct, urllib.parse, urllib.request, zipfile, zlib
URL='https://drive.google.com/uc?export=download&id=1OnSF3EULdJpFY4MwRZLgmXa6DauziR8W'
def download(destination):
    page=urllib.request.urlopen(URL,timeout=30).read().decode()
    query=dict(re.findall('name="([^"]+)" value="([^"]+)"',page))
    url='https://drive.usercontent.google.com/download?'+urllib.parse.urlencode(query)
    response=urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=-100000'}),timeout=45)
    assert response.status==206,'Server must support partial download'
    offset=int(response.headers['Content-Range'].split()[1].split('-')[0])
    archive=zipfile.ZipFile(io.BytesIO(response.read()))
    items=[i for i in archive.infolist() if '/atlas_20/' in i.filename and not i.is_dir() and '/Other/' not in i.filename]
    def get(info):
        path=pathlib.Path(destination)/info.filename
        if path.exists() and zlib.crc32(path.read_bytes())==info.CRC:return
        start=info.header_offset+offset
        r=urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={start}-{start+info.compress_size+4095}'}),timeout=45)
        assert r.status==206
        b=r.read();header=struct.unpack('<4s5H3L2H',b[:30]);n=30+header[-2]+header[-1]
        compressed=b[n:n+info.compress_size]
        data=zlib.decompress(compressed,-15) if info.compress_type==8 else compressed
        assert zlib.crc32(data)==info.CRC
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(get,items))
    print(len(items),'files;',sum(i.compress_size for i in items),'compressed bytes')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('destination');download(p.parse_args().destination)
