# -*- coding: utf-8 -*-
from __future__ import division, print_function

__author__           = "Dilawar Singh"
__copyright__        = "Copyright 2017-, Dilawar Singh"
__version__          = "1.0.0"
__maintainer__       = "Dilawar Singh"
__email__            = "dilawars@ncbs.res.in"
__status__           = "Development"

import sys
import os
import socket
import time
import tarfile
import tempfile
import argparse
from helper import log

def gen_prefix( msg, maxlength = 10 ):
    msg = '>%s' % msg
    if len(msg) < maxlength:
        msg += ' ' * (maxlength - len(msg))
    return msg[:maxlength].encode( 'utf-8' )

def write_data_to_socket(conn, msg):
    msg = b'%010d%s' % (len(msg), msg)
    conn.sendall(msg)

def gen_payload( args ):
    path = args['main_file']
    if not path:
        raise RuntimeError( 'No input fie' )
    if not os.path.isfile(path):
        raise RuntimeError( "File %s not found." % path )
        
    archive = os.path.join(tempfile.mkdtemp(), 'data.tar.bz2')

    # This mode (w|bz2) is suitable for streaming. The blocksize is default to
    # 20*512 bytes. We change this to 2048
    with tarfile.open(archive, 'w|bz2', bufsize=2048 ) as h:
        if os.path.isfile(path):
            h.add(path, os.path.basename(path))
        else:
            h.add(path)
        # add other files.
        for f in args['other_files'].split(';'):
            h.add(f, os.path.basename(f)) if f  else None

    with open(archive, 'rb') as f:
        data = f.read()
    return data

def get_n_bytes(conn, n):
    data = b''
    while len(data) < n:
        data += conn.recv(n-len(data), socket.MSG_WAITALL)
    return data

def read_msg(conn):
    # first get the first 10 byes
    nBytes = get_n_bytes(conn, 10)
    nBytes = int(nBytes)
    data = get_n_bytes(conn, nBytes)
    return data 

def save_bz2(conn, outfile):
    # first 6 bytes always tell how much to read next. Make sure the submit job
    # script has it
    d = get_n_bytes(conn, 10)
    if len(d) < 10:
        print( "[ERROR] Error in format. First 10 bytes are size of msg." )
        return 
    d = int(d)
    data = get_n_bytes(conn, d)
    with open(outfile, 'wb') as f:
        f.write(data)
    print( "[INFO ] Got total %d bytes." % len(data) )
    return data

def main( args ):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        host, port = args['server'].split(':')
        sock.connect( (host, int(port)) )
    except Exception as e:
        print( "[ERROR] Failed to connect to %s. Error %s "%(args['server'],e))
        return None

    sock.settimeout(1)
    data = None
    try:
        data = gen_payload( args )
    except Exception as e:
        log( "[ERROR] Failed to generate payload. Error: %s"%e)
        return None

    write_data_to_socket(sock, data)
    log( "[INFO ] Total data sent : %d bytes " % len(data) )
    while True:
        d = b''
        try:
            d = read_msg( sock )
        except socket.timeout as e:
            time.sleep(0.5)

        if b'>DONE SIMULATION' in d:
            break

    outfile = os.path.join(tempfile.mkdtemp(), 'res.tar.bz2')
    data = save_bz2(sock, outfile)
    return data, outfile

def submit_job(data):
    assert data['main_file'], 'Empty file name'
    return main(data)

if __name__ == '__main__':
    # Argument parser.
    description = '''Submit a job to moose server.'''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('path', metavar='path'
        , help = 'File or directory to execute on server.'
        )
    parser.add_argument('--main', '-m', nargs = '+'
        , required = False, default = []
        , help = 'In case of multiple files, scripts to execute'
                ' on the server, e.g. -m file1.py -m file2.py.'
                ' If not given, server will try to guess the best option.'
        )
    parser.add_argument('--server', '-s'
        , required = False, type=str, default='localhost:31417'
        , help = 'IP address and PORT number of moose server e.g.'
                 ' 172.16.1.2:31416'
        )
    class Args: pass
    args = Args()
    parser.parse_args(namespace=args)
    main( vars(args) )
