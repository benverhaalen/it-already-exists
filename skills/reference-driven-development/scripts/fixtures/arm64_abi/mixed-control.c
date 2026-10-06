#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
typedef double (*mixed_reader)(int,int,int,int,int,int,int,int,int,int,
    double,double,double,double,double,double,double,double,double,void*,bool);
extern double android_mixed_call(mixed_reader);
__attribute__((noinline)) double darwin_mixed(
    int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,
    double u,double v,double w,double x,double y,double z,double p,double q,double r,
    void *handle,bool enabled) {
  if (a!=1 || b!=2 || c!=3 || d!=4 || e!=5 || f!=6 || g!=7 || h!=8 ||
      i!=-11 || j!=22 || u!=1 || v!=2 || w!=3 || x!=4 || y!=5 || z!=6 ||
      p!=7 || q!=8 || r!=9 || (uintptr_t)handle!=12345 || !enabled) return -1;
  return 45.5;
}
__attribute__((noinline,ms_abi)) double compiler_mixed(
    int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,
    double u,double v,double w,double x,double y,double z,double p,double q,double r,
    void *handle,bool enabled) {
  return darwin_mixed(a,b,c,d,e,f,g,h,i,j,u,v,w,x,y,z,p,q,r,handle,enabled);
}
int main(void) {
  double direct=android_mixed_call(darwin_mixed);
  double adapted=android_mixed_call((mixed_reader)compiler_mixed);
  printf("MIXED_COMPILER_BRIDGE direct=%g adapted=%g expected=45.5\n",direct,adapted);
  return direct==-1 && adapted==45.5 ? 0 : 1;
}
