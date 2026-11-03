import math, numpy as np, sys
exec(open('t3.py').read().split('j=3\n')[0])
j=4
def run(h,E,shift,bs):
    out=[]
    for b in bs:
        a=b-j; N=b**3+2*b*b; n=N-97-shift*a
        a,c=col(b,j,h,E,n); out.append((b,bad(a,b,n,c)))
    return out
if __name__=='__main__':
    for h in (4,5,6):
        for E in (2,4,6,8,10):
            r=run(h,E,1,[49,51,53,55])
            print('h',h,'E',E,r,flush=True)
