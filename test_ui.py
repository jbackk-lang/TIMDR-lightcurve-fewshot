import json,unittest,threading,urllib.request,urllib.error
from pathlib import Path
import numpy as np
from ui_import import inspect_text,parse_table
from ui_analysis import analyze,search_period,signal_view
from ui_server import Server

ROOT=Path(__file__).resolve().parent

class ImportTests(unittest.TestCase):
    def test_semicolon_decimal_comma(self):
        text='czas;mag;blad\n1,5;12,2;0,02\n2,5;12,3;0,03'
        t=inspect_text(text);a,stats,_=parse_table(text,t['suggest'])
        np.testing.assert_allclose(a[:,0],[1.5,2.5]);self.assertEqual(stats['bad_error'],0)
    def test_aavso_multiple_filters_and_stars(self):
        text='#TYPE=EXTENDED\n#DATE=JD\n#NAME,DATE,MAG,MERR,FILT\nA,2450000,12,.02,I\nA,2450001,13,.02,I\nB,2450002,12,.02,V'
        t=inspect_text(text)
        with self.assertRaises(ValueError):parse_table(text,t['suggest'])
        a,stats,_=parse_table(text,t['suggest'],band='I',object_name='A')
        self.assertEqual(len(a),2);self.assertEqual(stats['filtered_rows'],1)
    def test_iso_and_invalid_magnitude(self):
        text='time,magnitude,error\n2026-09-01T00:00:00Z,12,.1\n2026-09-02T00:00:00Z,13,.1\nnot-a-date,12,.1\n2026-09-03T00:00:00Z,<14,.1'
        a,s,_=parse_table(text,inspect_text(text)['suggest'],'iso')
        self.assertAlmostEqual(a[1,0]-a[0,0],1);self.assertEqual(s['bad_time'],1);self.assertEqual(s['limits'],1)
    def test_duplicates_and_missing_uncertainties_visible(self):
        text='time,magnitude,error\n2,12,.1\n1,10,.1\n1,12,.1\n3,13,0'
        a,s,_=parse_table(text,inspect_text(text)['suggest'])
        self.assertEqual(s['duplicates'],1);self.assertEqual(s['unsorted_steps'],1)
        self.assertEqual(s['bad_error'],1);self.assertTrue(np.isnan(a[-1,2]));self.assertEqual(a[0,1],11)
    def test_no_automatic_flux_mapping(self):
        t=inspect_text('time,flux,error\n1,100,.2\n2,110,.2')
        self.assertIsNone(t['suggest']['magnitude'])

class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=(ROOT/'examples/ogle_test_curve.csv').read_text()
        cls.mapping=inspect_text(cls.text)['suggest']
        cls.p=json.loads((ROOT/'examples/metadata.json').read_text())['period']
    def payload(self,**kwargs):return dict(text=self.text,mapping=self.mapping,period=self.p,declared_band='I',**kwargs)
    def test_example_and_saved_predictions(self):
        r=analyze(self.payload());self.assertTrue(r['quality']['ready'])
        self.assertEqual(r['classification']['timdr_lda']['label'],'RRab')
        for arm,path in [('timdr_lda','prediction_timdr.json'),('classical_rf','prediction_rf.json')]:
            old=json.loads((ROOT/'examples'/path).read_text())
            for k,v in old['scores'].items():self.assertAlmostEqual(v,r['classification'][arm]['scores'][k],places=10)
    def test_unknown_period_never_classifies(self):
        p=self.payload();p['period']=None;r=analyze(p)
        self.assertIsNone(r['classification']);self.assertNotIn('signal',r)
    def test_missing_errors_blocks_even_with_points(self):
        p=self.payload();p['mapping']={**self.mapping,'error':None};r=analyze(p)
        self.assertIsNone(r['classification']);self.assertEqual(r['stats']['bad_error'],169)
    def test_other_band_needs_explicit_experimental_mode(self):
        p=self.payload();p['declared_band']='V';r=analyze(p);self.assertIsNone(r['classification'])
        p['allow_experimental']=True;self.assertIsNotNone(analyze(p)['classification'])
    def test_sparse_and_constant_fail_gracefully(self):
        p=self.payload();p['text']='time,magnitude,error\n'+'\n'.join(f'{i},12,.02' for i in range(10))
        r=analyze(p);self.assertIsNone(r['classification']);self.assertGreaterEqual(len(r['quality']['blockers']),2)
    def test_period_recovery_and_bounded_grid(self):
        rng=np.random.default_rng(91);t=np.sort(rng.uniform(0,50,350));period=.73
        a=np.c_[t,12+np.sin(2*np.pi*t/period)+rng.normal(0,.03,len(t)),np.full(len(t),.03)]
        r=search_period(a,.5,1);self.assertLess(abs(r['candidates'][0]['period']-period),.002)
        with self.assertRaises(ValueError):search_period(a,.000001,100)
    def test_sieve_really_attenuates_not_rejects_points(self):
        a,_,_=parse_table(self.text,self.mapping);s=signal_view(a,self.p)
        self.assertTrue(np.all(s['harmonic_after']<=s['harmonic_amplitude']+1e-12))
        self.assertEqual(sum(s['counts']),len(a));self.assertTrue(0<=s['attenuated_energy_pct']<=100)

class TutorialTests(unittest.TestCase):
    def test_problem_examples_block_classification(self):
        samples=json.loads((ROOT/'examples/ui_examples.json').read_text(encoding='utf-8'))
        for key in ('few-points','phase-gaps','large-errors','unknown-period'):
            sample=next(s for s in samples if s['key']==key)
            r=analyze(dict(text=sample['text'],mapping=inspect_text(sample['text'])['suggest'],period=sample['period'],declared_band='I'))
            self.assertIsNone(r['classification'],key)

    def test_four_real_examples_can_be_analyzed(self):
        samples=json.loads((ROOT/'examples/ui_examples.json').read_text(encoding='utf-8'))
        for sample in samples[:4]:
            r=analyze(dict(text=sample['text'],mapping=inspect_text(sample['text'])['suggest'],period=sample['period'],declared_band='I'))
            self.assertIsNotNone(r['classification'],sample['key'])

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=Server(('127.0.0.1',0));cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def test_home_and_local_token(self):
        text=urllib.request.urlopen(self.url).read().decode();self.assertIn(self.server.token,text);self.assertNotIn('__TOKEN__',text)
    def test_api_rejects_other_origin(self):
        req=urllib.request.Request(self.url+'/api/inspect',data=b'{}',headers={'Origin':'https://example.com','X-Local-Token':self.server.token})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
    def test_api_inspect(self):
        req=urllib.request.Request(self.url+'/api/inspect',data=json.dumps({'text':'time,mag,error\n1,2,.1\n2,3,.1'}).encode(),headers={'X-Local-Token':self.server.token})
        result=json.load(urllib.request.urlopen(req));self.assertEqual(result['suggest']['time'],0)
    def test_no_arbitrary_file_download(self):
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.url+'/models/timdr_lda.joblib')
        self.assertEqual(e.exception.code,404)

if __name__=='__main__':unittest.main()
