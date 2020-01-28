#!/usr/bin/env python3

import os
from lexdriver import run

def main():
    to_run = []
    for _, _, filenames in os.walk('test/fixtures/'):
        for filename in filenames:
            if filename.endswith('.src'):
                to_run.append('test/fixtures/' + filename)  
    for f in to_run:
        with open(f) as f_:
            print('Lexical analysis for {}'.format(f))
            run(f_)
        
        with open(f.replace('.src', '.outlextokens')) as f_:
            print('Tokens:')
            print(f_.read())
        print('-----------------------')
        with open(f.replace('.src', '.outlexerrors')) as f_:
            print('Errors:')
            print(f_.read())
        print('----------------------------------------------')



if __name__ == '__main__':
    main()