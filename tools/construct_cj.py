import sys, math, numpy as np
def va(x,a):
    e=0
    while x%a==0: x//=a; e+=1
    return e
def col_j(b,j,h):
    a=b-j; n=b**3+2*b*b-j*j*(j+2)-1
    col=np.zeros(n+1,dtype=np.int8)
    for x in range(1,n+1):
        t=va(x,a)
        if t==0: col[x]=0 if (x<=a*b-1 or x>=n-2*b) else 2
        elif t==1: col[x]=1 if x//a<=b*(b+1) else 2
        else:
            q=x//(a*a); col[x]=0 if q<=b else (1 if q<=b+h else 2)
    return a,n,col
def bad(a,b,n,col):
    s=1;tot=0
    while b*s<=n-1 and a*s<=n:
        d=b*s;z=a*s;y=np.arange(1,n-d+1)
        tot+=int(((col[y]==col[y+d])&(col[y]==col[z])).sum()); s+=1
    return tot
if __name__ != "__main__": pass
j=int(sys.argv[1]) if __name__=="__main__" else 0; h=int(sys.argv[2]) if __name__=="__main__" else 0
if __name__=="__main__":
  res=[]
  for b in map(int,sys.argv[3:]):
    a=b-j
    if a<2 or math.gcd(a,b)!=1: continue
    a,n,col=col_j(b,j,h); res.append((b,bad(a,b,n,col)))
  print('j',j,'h',h,res,flush=True)
