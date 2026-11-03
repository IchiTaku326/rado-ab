# -*- coding: utf-8 -*-
"""Explicit k-colouring of [1, a^k+a^(k-1)-2a] with no monochromatic solution of a(x-y)=(a-1)z (2026-10-27).
Generalises Lemma 4.2 of arXiv:2210.03262 (k=3) to every k. Levels v_a>=1: colour v_a-1. Units (v_a=0): blocks of colours
B_2..B_{k-1}, B_k, B_{k-1}..B_2 with lengths (a-1)a^(j-1). Checks every solution. Usage: python tools\\construct_b1.py"""
import numpy as np, sys
def va(x,a):
    e=0
    while x%a==0: x//=a; e+=1
    return e
def colouring(a,k):
    n=a**k+a**(k-1)-2*a
    col=np.zeros(n+1,dtype=np.int16)
    # unit blocks: B_2..B_{k-1}, B_k (middle), B_{k-1}..B_2 ; colour of level j = j-1
    blocks=[(j,(a-1)*a**(j-1)) for j in range(2,k)]
    seq=blocks+[(k,(a-1)*a**(k-1))]+blocks[::-1]
    pos=1; unitcol=np.zeros(n+1,dtype=np.int16)
    for j,L in seq:
        unitcol[pos:pos+L]=j-1; pos+=L
    assert pos==n+1,(pos,n)
    for x in range(1,n+1):
        v=va(x,a); col[x]= unitcol[x] if v==0 else v-1
    return n,col
def check(a,b,k,n,col):
    bad=0
    s=1
    while a*s<=n and b*s<=n-1:
        z=a*s; d=b*s
        y=np.arange(1,n-d+1)
        m=(col[y]==col[y+d])&(col[y]==col[z])
        bad+=int(m.sum()); s+=1
    return bad
for k in (3,4,5):
    for a in range(3,10):
        n,col=colouring(a,k)
        if n>60000: continue
        print(f'k={k} a={a} b={a-1} n={n} colours={len(set(col[1:].tolist()))} monochromatic solutions={check(a,a-1,k,n,col)}',flush=True)
