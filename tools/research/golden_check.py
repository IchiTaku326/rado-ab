import numpy as np
from math import gcd
from rec_template import T2, step
from rec_template_check import checkv
def L_seq(a,b,k):
    L=b*b+b+1; out={2:L}
    for kk in range(3,k+1): L=b*(L+2*a)+1; out[kk]=L
    return out
def tmpl(a,b,k):
    n,C=T2(a,b); Ls=L_seq(a,b,k)
    for kk in range(3,k+1):
        C=step(a,b,C,Ls[kk]-1,kk)
    return C
bad=[];cnt=0
for b in range(3,14):
    for a in range(2,b):
        if gcd(a,b)!=1 or a*a+a*b>b*b: continue
        for k in (3,4,5):
            if k==5 and b>9: continue
            C=tmpl(a,b,k); m=checkv(a,b,C); cnt+=1
            if m: bad.append((a,b,k,m))
print('checked',cnt,'bad',bad)
