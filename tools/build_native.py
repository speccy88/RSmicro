#!/usr/bin/env python3
import argparse
from rsmicro.native.build import build_native

def main():
    p=argparse.ArgumentParser(); p.add_argument("--build-dir",default="build"); p.add_argument("--clean",action="store_true"); p.add_argument("--debug",action="store_true"); p.add_argument("--release",action="store_true"); p.add_argument("--sanitize",action="store_true"); a=p.parse_args()
    print(build_native(a.build_dir,a.clean,"Debug" if a.debug else "Release",a.sanitize))
if __name__=="__main__": main()
