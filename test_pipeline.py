import unittest
import numpy as np
from features import extract
from prepare import clean
from benchmark import split

class PipelineTests(unittest.TestCase):
    def curve(self,noise=.02):
        rng=np.random.default_rng(58);t=np.sort(rng.uniform(0,100,1200)); p=1.37
        y=15+np.sin(2*np.pi*t/p)+.3*np.sin(4*np.pi*t/p+.5)+rng.normal(0,noise,len(t))
        return np.c_[t,y,np.full(len(t),max(noise,.001))],p

    def test_clock_translation_invariance(self):
        a,p=self.curve();b=a.copy();b[:,0]+=2450000
        for k,v in extract(a,p).items(): np.testing.assert_allclose(v,extract(b,p)[k],atol=1e-6)

    def test_magnitude_offset_invariance(self):
        a,p=self.curve();b=a.copy();b[:,1]+=8
        for k,v in extract(a,p).items(): np.testing.assert_allclose(v,extract(b,p)[k],atol=1e-9)

    def test_coherence_detects_clock_failure(self):
        a,p=self.curve();good=extract(a,p)['timdr'][67:75];bad=extract(a,p*1.13)['timdr'][67:75]
        self.assertGreater(good[0],.99);self.assertGreater(good[0]-bad[0],.3)

    def test_noise_is_less_coherent(self):
        a,p=self.curve();a[:,1]=np.random.default_rng(22).normal(size=len(a))
        self.assertLess(extract(a,p)['timdr'][67:75].mean(),.8)

    def test_duplicate_averaging(self):
        a=clean(np.array([[2,4,1],[1,2,1],[1,4,1],[3,8,-1]]))
        np.testing.assert_allclose(a[:,0],[1,2]);self.assertEqual(a[0,1],3)

    def test_nested_disjoint_support(self):
        m=[dict(y=c,split='support' if i<300 else 'test') for c in range(4) for i in range(500)]
        small,te,y=split(m,4,0);large,te2,_=split(m,160,0)
        self.assertEqual(len(set(small)&set(te)),0);self.assertTrue(set(small)<=set(large))
        self.assertEqual(len(te),800);np.testing.assert_array_equal(te,te2)
        np.testing.assert_array_equal(np.bincount(y[large]),[160]*4)

if __name__=='__main__': unittest.main()
