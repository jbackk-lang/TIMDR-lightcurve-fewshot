"""Experimental CCD diagnostics and differential aperture photometry.

Inspired by I2D's separate detector overlays; no image manipulation classifier.
Photometry always uses original pixels, never the display stretch or a TIMDR sieve.
"""
import base64, io, csv, math, hashlib
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
from astropy.io import fits
from astropy.time import Time
from PIL import Image, UnidentifiedImageError

MAX_PIXELS=4_000_000
MAX_BYTES=24_000_000

def number(value,name,lo,hi):
    try:value=float(value)
    except (ValueError,TypeError):raise ValueError(f'Podaj poprawną wartość: {name}.')
    if not math.isfinite(value) or not lo<=value<=hi:raise ValueError(f'{name}: zakres {lo}–{hi}.')
    return value

def load(item):
    if not isinstance(item,dict):raise ValueError('Nieprawidłowy plik.')
    name=str(item.get('name','obraz'))[:160]
    try:data=base64.b64decode(item.get('data',''),validate=True)
    except Exception:raise ValueError('Nieprawidłowe kodowanie obrazu.')
    if not data or len(data)>MAX_BYTES:raise ValueError('Limit pliku: 24 MB.')
    header={};scientific=name.lower().endswith(('.fits','.fit','.fts'))
    try:
        if scientific:
            with fits.open(io.BytesIO(data),memmap=False) as hdus:
                hdu=hdus[0]
                if not isinstance(hdu,fits.PrimaryHDU) or hdu.header.get('NAXIS')!=2:raise ValueError('FITS: wymagany pojedynczy obraz 2D w głównym HDU.')
                w=int(hdu.header['NAXIS1']);h=int(hdu.header['NAXIS2'])
                if w*h>MAX_PIXELS:raise ValueError('Limit: 4 miliony pikseli.')
                header=dict(hdu.header);a=np.array(hdu.data,dtype=float)
        else:
            with Image.open(io.BytesIO(data)) as im:
                if im.width*im.height>MAX_PIXELS:raise ValueError('Limit: 4 miliony pikseli.')
                if im.format not in ('PNG','JPEG','TIFF'):raise ValueError('Obsługiwane formaty: FITS, PNG, JPEG, TIFF.')
                a=np.asarray(im.convert('L'),dtype=float)
    except (OSError,UnidentifiedImageError) as e:raise ValueError('Nie można odczytać obrazu.') from e
    if a.ndim!=2 or min(a.shape)<32 or not np.isfinite(a).all():raise ValueError('Obraz musi mieć co najmniej 32×32 piksele i nie zawierać NaN/Inf.')
    return a,header,scientific,name

def background(a):
    values=a.ravel()[::max(1,a.size//200000)]
    for _ in range(3):
        med=np.median(values);sigma=1.4826*np.median(abs(values-med))
        if sigma<=0:break
        values=values[abs(values-med)<3*sigma]
    return float(med),max(float(sigma),1e-6)

def inspect(item):
    a,h,scientific,name=load(item);bg,sigma=background(a)
    smooth=gaussian_filter(a,1)
    mask=(smooth==maximum_filter(smooth,9))&(smooth>bg+5*sigma)
    mask[:12]=False;mask[-12:]=False;mask[:,:12]=False;mask[:,-12:]=False
    yy,xx=np.nonzero(mask);order=np.argsort(smooth[yy,xx])[::-1][:100]
    stars=[]
    for i in order:
        x,y=int(xx[i]),int(yy[i]);patch=np.maximum(a[y-3:y+4,x-3:x+4]-bg,0)
        gy,gx=np.mgrid[-3:4,-3:4];mass=patch.sum()
        width=float(2.355*np.sqrt(((gx*gx+gy*gy)*patch).sum()/max(mass,1)/2))
        stars.append(dict(x=x,y=y,peak=float(a[y,x]),fwhm=width,flags=['punkt bardzo wąski / możliwy gorący piksel'] if width<1.5 else []))
    lo,hi=np.percentile(a,[5,99.8]);display=np.arcsinh(np.clip((a-lo)/max(hi-lo,1e-9),0,1)*10)/np.arcsinh(10)
    im=Image.fromarray(np.uint8(display*255));im.thumbnail((900,900));out=io.BytesIO();im.save(out,format='PNG')
    warnings=[]
    if not scientific:warnings.append('Obraz poglądowy. JPEG/PNG/TIFF mogą być przetworzone; fotometria w tym prototypie wymaga liniowych FITS w ADU.')
    if len(stars)<3:warnings.append('Mało kandydatów: sprawdź ekspozycję, ostrość i czy zdjęcie przedstawia pole gwiazdowe.')
    if not h.get('DATE-OBS') and not h.get('JD') and not h.get('MJD-OBS'):warnings.append('Brak czasu obserwacji w nagłówku.')
    warnings.append('Detekcje są kandydatami na źródła. Brak identyfikacji katalogowej i automatycznego potwierdzenia ostrości lub nasycenia.')
    return dict(name=name,width=a.shape[1],height=a.shape[0],background=bg,noise=sigma,stars=stars,warnings=warnings,scientific=scientific,preview='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode())

def measure(a,x,y,r,gain,saturation):
    x=number(x,'X',0,a.shape[1]-1);y=number(y,'Y',0,a.shape[0]-1)
    # Only tiny residual shifts are accepted; input frames must already be registered.
    ix,iy=int(round(x)),int(round(y));margin=int(math.ceil(2.5*r))+4
    if min(ix,iy,a.shape[1]-1-ix,a.shape[0]-1-iy)<margin:raise ValueError('Gwiazda jest zbyt blisko brzegu.')
    patch=a[iy-3:iy+4,ix-3:ix+4];weight=np.maximum(patch-np.median(patch),0)
    gy,gx=np.mgrid[-3:4,-3:4]
    if weight.sum()<=0:raise ValueError('Nie znaleziono gwiazdy w wybranym miejscu.')
    dx=float((gx*weight).sum()/weight.sum());dy=float((gy*weight).sum()/weight.sum())
    if np.hypot(dx,dy)>1.5:raise ValueError('Przesunięcie gwiazdy: wyrównaj zdjęcia przed pomiarem.')
    x+=dx;y+=dy
    sub=a[iy-margin:iy+margin+1,ix-margin:ix+margin+1]
    yy,xx=np.mgrid[iy-margin:iy+margin+1,ix-margin:ix+margin+1]
    d=np.hypot(xx-x,yy-y);ap=d<=r;sky=(d>=1.7*r)&(d<=2.5*r)
    if np.max(sub[ap])>=saturation:raise ValueError('Gwiazda osiągnęła ustawiony próg nasycenia.')
    skyvals=sub[sky];med=np.median(skyvals);sig=max(1.4826*np.median(abs(skyvals-med)),1e-6)
    skyvals=skyvals[abs(skyvals-med)<3*sig]
    if len(skyvals)<20:raise ValueError('Za mało pikseli tła.')
    bg=float(skyvals.mean());variance=float(skyvals.var(ddof=1));n=int(ap.sum())
    flux=float(sub[ap].sum()-n*bg)
    err=np.sqrt(max(flux,0)/gain+(n+n*n/len(skyvals))*variance)
    if flux<=0 or flux/err<5:raise ValueError('Sygnał gwiazdy jest za słaby (S/N < 5).')
    return flux,float(err)

def midtime(h):
    if str(h.get('TIMESYS','UTC')).upper()!='UTC':raise ValueError('Prototyp wymaga czasu UTC w nagłówkach FITS.')
    exp=number(h.get('EXPTIME'),'EXPTIME w sekundach',.001,86400)
    try:
        if 'JD' in h:t=Time(float(h['JD']),format='jd',scale='utc')
        elif 'MJD-OBS' in h:t=Time(float(h['MJD-OBS']),format='mjd',scale='utc')
        else:t=Time(str(h['DATE-OBS']),scale='utc')
        result=float(t.jd)+exp/172800
        if not math.isfinite(result):raise ValueError()
        return result
    except Exception:raise ValueError('Brak poprawnego początku ekspozycji DATE-OBS, JD lub MJD-OBS.')

def series(payload):
    files=payload.get('files',[])
    if not isinstance(files,list) or not 2<=len(files)<=160:raise ValueError('Wgraj 2–160 plików FITS (łącznie do 24 MB).')
    if not all(isinstance(f,dict) and isinstance(f.get('data'),str) for f in files):raise ValueError('Nieprawidłowa lista plików.')
    if sum(len(f.get('data','')) for f in files)>32_000_000:raise ValueError('Łączny limit: 24 MB danych.')
    if payload.get('calibrated') is not True:raise ValueError('Potwierdź liniowość, kalibrację, wyrównanie zdjęć i jednostkę ADU.')
    gain=number(payload.get('gain'),'Gain [elektrony/ADU]',.01,100)
    sat=number(payload.get('saturation'),'Próg nasycenia [ADU]',1,1e9)
    r=number(payload.get('radius',4),'Promień apertury [px]',2,12)
    target=payload.get('target',{});ref=payload.get('reference',{})
    tx=number(target.get('x'),'X obiektu',0,MAX_PIXELS);ty=number(target.get('y'),'Y obiektu',0,MAX_PIXELS)
    rx=number(ref.get('x'),'X odniesienia',0,MAX_PIXELS);ry=number(ref.get('y'),'Y odniesienia',0,MAX_PIXELS)
    if np.hypot(tx-rx,ty-ry)<5*r:raise ValueError('Wybierz oddzielone gwiazdy: minimum 5 promieni apertury.')
    points=[];rejected=[];shape=None;band=None;times=set()
    for item in files:
        a,h,science,name=load(item)
        if not science:raise ValueError('Seria pomiarowa wymaga wyłącznie plików FITS.')
        if str(h.get('BUNIT','ADU')).strip().upper() not in ('ADU','COUNT','COUNTS'):raise ValueError('Dane muszą być w ADU, nie w elektronach lub strumieniu na sekundę.')
        if h.get('BAYERPAT'):raise ValueError('Surowa mozaika Bayera nie jest obsługiwana: przygotuj oddzielne, liniowe pasmo.')
        if shape is None:shape=a.shape;band=str(h.get('FILTER','nieznane'))
        if a.shape!=shape or str(h.get('FILTER','nieznane'))!=band:raise ValueError('Zdjęcia muszą mieć ten sam rozmiar i pasmo.')
        t=midtime(h)
        if t in times:raise ValueError('Powtórzony czas ekspozycji. Sprawdź nagłówki FITS.')
        times.add(t)
        try:
            ft,et=measure(a,tx,ty,r,gain,sat);fr,er=measure(a,rx,ry,r,gain,sat)
            points.append(dict(name=name,time=t,magnitude=float(-2.5*np.log10(ft/fr)),error=float(2.5/np.log(10)*np.hypot(et/ft,er/fr))))
        except ValueError as e:rejected.append(dict(name=name,reason=str(e)))
    points.sort(key=lambda p:p['time'])
    out=io.StringIO();writer=csv.writer(out);writer.writerow(['time','magnitude','error'])
    for p in points:writer.writerow([p['time'],p['magnitude'],p['error']])
    return dict(points=points,rejected=rejected,csv=out.getvalue(),band=band,settings=dict(target={'x':tx,'y':ty},reference={'x':rx,'y':ry},gain=gain,saturation=sat,radius=r,calibrated=True),input_sha256=[dict(name=f.get('name',''),sha256=hashlib.sha256(base64.b64decode(f['data'])).hexdigest()) for f in files],warnings=['Magnitudo względne względem jednej gwiazdy odniesienia; jej stałość nie została potwierdzona.','Błędy obejmują szum fotonowy i lokalne tło; nie obejmują błędów kalibracji ani scyntylacji.','Czas: JD UTC środka ekspozycji, bez korekcji barycentrycznej.','Brak automatycznej rejestracji, kontroli sąsiednich źródeł i korekty PSF. Zmienny seeing może tworzyć pozorną zmienność.'])

def demo(kind="variable"):
    if kind not in ("variable","constant","saturated"):raise ValueError("Nieznany przykład.")
    rng=np.random.default_rng(713);yy,xx=np.mgrid[:96,:128];files=[]
    for i in range(96):
        a=np.full((96,128),400.)
        for x,y,flux in [(32,40,14000*(1+(.0 if kind=="constant" else .2)*np.sin(2*np.pi*i/32))),(86,55,19000),(72,25,9000)]:
            a+=flux/(2*np.pi*1.35**2)*np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.35**2))
        a=rng.poisson(a).astype(np.float32)
        if kind=="saturated" and i in (5,10,15):a[40,32]=65000
        h=fits.Header({'JD':2460000+i*.56/32,'EXPTIME':30.,'BUNIT':'ADU','FILTER':'SIMULATED'})
        b=io.BytesIO();fits.PrimaryHDU(a,h).writeto(b)
        files.append(dict(name=f'symulacja_{i:02d}.fits',data=base64.b64encode(b.getvalue()).decode()))
    return dict(files=files,target={'x':32,'y':40},reference={'x':86,'y':55},gain=1,saturation=60000,radius=4,calibrated=True,period=.56)


def folder_series(root,example=None):
    from pathlib import Path
    root=Path(root).resolve()
    if example is not None and example not in ('variable','constant','saturated'):raise ValueError('Nieznany przykład.')
    folder=root/'images'/('examples/'+example if example else 'inbox')
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):raise ValueError('Nieprawidłowy folder zdjęć.')
    files=[];total=0
    for path in sorted(folder.glob('*')):
        if path.suffix.lower() not in ('.fits','.fit','.fts','.png','.jpg','.jpeg','.tif','.tiff') or not path.is_file():continue
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):raise ValueError('Dowiązania do zdjęć nie są obsługiwane.')
        total+=path.stat().st_size
        if total>MAX_BYTES or len(files)>=160:raise ValueError('Folder przekracza limit 160 zdjęć lub 24 MB.')
        files.append(dict(name=path.name,data=base64.b64encode(path.read_bytes()).decode()))
    if not files:raise ValueError('Folder jest pusty. Skopiuj zdjęcia do: '+str(folder))
    result=dict(files=files,folder=str(folder))
    if example:result.update(target={'x':32,'y':40},reference={'x':86,'y':55},gain=1,saturation=60000,radius=4,calibrated=True,period=.56)
    return result
