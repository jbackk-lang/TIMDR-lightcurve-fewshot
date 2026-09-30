import base64,io,unittest,copy,json,threading,urllib.request
import numpy as np
from astropy.io import fits
from sky_images import demo,inspect,series,load,measure,midtime
from ui_server import Server

def change(item,**updates):
    data=base64.b64decode(item['data'])
    with fits.open(io.BytesIO(data)) as hdus:
        for k,v in updates.items():hdus[0].header[k]=v
        b=io.BytesIO();hdus.writeto(b)
    return dict(name=item['name'],data=base64.b64encode(b.getvalue()).decode())

class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.demo=demo()
    def test_detect_known_stars(self):
        d=inspect(self.demo['files'][0])
        for x,y in [(32,40),(86,55),(72,25)]:self.assertTrue(any(np.hypot(s['x']-x,s['y']-y)<2 for s in d['stars']))
    def test_recover_injected_variability(self):
        d=series(self.demo);self.assertEqual(len(d['points']),96);self.assertEqual(d['rejected'],[])
        truth=-2.5*np.log10(14000*(1+.2*np.sin(2*np.pi*np.arange(96)/32))/19000)
        measured=np.array([p['magnitude'] for p in d['points']]);residual=measured-truth
        self.assertLess(np.std(residual),.035)
        self.assertLess(abs(np.median(residual)),.035)
        self.assertTrue(all(p['error']>0 for p in d['points']))
    def test_constant_source_stays_constant(self):
        p=copy.deepcopy(self.demo);p['target']={'x':72,'y':25};p['radius']=3
        d=series(p);self.assertEqual(len(d['points']),96)
        self.assertLess(np.std([r['magnitude'] for r in d['points']]),.05)
    def test_calibration_confirmation(self):
        with self.assertRaises(ValueError):series({**self.demo,'calibrated':False})
    def test_same_star_rejected(self):
        with self.assertRaises(ValueError):series({**self.demo,'reference':self.demo['target']})
    def test_saturation_explained(self):
        d=series({**self.demo,'saturation':500});self.assertEqual(len(d['points']),0)
        self.assertTrue(all('nasycenia' in p['reason'] for p in d['rejected']))
    def test_duplicate_time(self):
        with self.assertRaisesRegex(ValueError,'Powtórzony'):series({**self.demo,'files':[self.demo['files'][0]]*2})
    def test_filter_mismatch(self):
        with self.assertRaisesRegex(ValueError,'pasmo'):series({**self.demo,'files':[self.demo['files'][0],change(self.demo['files'][1],FILTER='V')]})
    def test_bayer_rejected(self):
        with self.assertRaisesRegex(ValueError,'Bayer'):series({**self.demo,'files':[change(self.demo['files'][0],BAYERPAT='RGGB'),self.demo['files'][1]]})
    def test_missing_time_and_wrong_scale(self):
        for h in ({'EXPTIME':20},{'JD':2460000,'EXPTIME':20,'TIMESYS':'TDB'}):
            with self.assertRaises(ValueError):midtime(h)
        self.assertAlmostEqual(midtime({'JD':2460000,'EXPTIME':60}),2460000+30/86400)
    def test_edges_and_invalid_gain(self):
        with self.assertRaises(ValueError):measure(load(self.demo['files'][0])[0],1,1,4,1,60000)
        with self.assertRaises(ValueError):series({**self.demo,'gain':'nan'})
    def test_disk_examples_and_rejections(self):
        from pathlib import Path
        from sky_images import folder_series
        root=Path(__file__).resolve().parent
        constant=series(folder_series(root,'constant'))
        self.assertEqual(len(constant['points']),96)
        self.assertLess(np.std([p['magnitude'] for p in constant['points']]),.05)
        saturated=series(folder_series(root,'saturated'))
        self.assertEqual(len(saturated['points']),93)
        self.assertEqual(len(saturated['rejected']),3)
        with self.assertRaises(ValueError):folder_series(root,'../../')

    def test_images_to_main_analysis(self):
        from ui_analysis import analyze
        d=series(self.demo)
        result=analyze(dict(text=d['csv'],mapping={'time':0,'magnitude':1,'error':2},period=.56,declared_band='SIMULATED',allow_experimental=True))
        self.assertIsNotNone(result['classification'],result['quality'])
        self.assertTrue(result['quality']['ready'])

    def test_api(self):
        server=Server(('127.0.0.1',0));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            root=f'http://127.0.0.1:{server.server_port}'
            with urllib.request.urlopen(root+'/images') as r:self.assertIn(server.token.encode(),r.read())
            req=urllib.request.Request(root+'/api/images/inspect',data=json.dumps({'file':self.demo['files'][0]}).encode(),headers={'X-Local-Token':server.token,'Content-Type':'application/json'})
            with urllib.request.urlopen(req) as r:self.assertTrue(json.load(r)['scientific'])
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
