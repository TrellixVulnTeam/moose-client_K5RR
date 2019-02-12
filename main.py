# -*- coding: utf-8 -*-
from __future__ import division, print_function
    
__author__           = "Dilawar Singh"
__copyright__        = "Copyright 2017-, Dilawar Singh"
__version__          = "1.0.0"
__maintainer__       = "Dilawar Singh"
__email__            = "dilawars@ncbs.res.in"
__status__           = "Development"

import pathlib
import client
import tarfile
import helper
import layout
import multiprocessing as mp

def display_results(bzfile, window):
    helper.log( "Displaying results saved in %s" % bzfile )
    cwd = pathlib.Path(bzfile).parent
    with tarfile.open(bzfile, 'r') as f:
        f.extractall(path=cwd)
    images = helper.find_images_pil(cwd)
    if len(images) > 0:
        layout.draw_canvas(window.FindElement('results'), images)
    else:
        helper.log( "No images were returned by the server." )

def client_process(values, done, q, lock):
    if not lock.acquire(timeout=1):
        helper.log("Other process is running.")
        q.put(None)
        done.value == 1
        return 
    res = client.submit_job(values)
    q.put(res)
    done.value = 1
    lock.release()
    print( 'Complete.' )
    return

def main(args):
    window = layout.mainWindow 

    if args['server']:
        window.FindElement('server').Update(args['server'])
    if args['input']:
        window.FindElement('main_file').Update(args['input'])

    # Prepare for multiprocessing. Only One request can be served at a time.
    lock = mp.Lock()
    res = mp.Queue()
    clientDone = mp.Value('d', 0)

    while True:
        event, values = window.Read()  
        print(event, values)
        if event is None or event == 'Exit':  
            lock.release()
            break  
        if event == 'Submit':  
            p = mp.Process(target=client_process, args=(values, clientDone, res, lock))
            p.start()
            if clientDone.value == 1:
                clientDone.value = 0
                response = res.get()
                if response is None:
                    helper.log( "[INFO ] Failed to recieve any data." )
                else:
                    data, bzfile = response
                    helper.log( "All done. Recieved %s bytes of data." % len(data) )
                    display_results( bzfile, window )
        else:
            helper.log( 'Unsupported event' )

        for x in ['server', 'main_file', 'other_files']:
            window.FindElement(x).Update(values.get(x,''))
    window.Close()

if __name__ == '__main__':
    import argparse
    # Argument parser.
    description = '''GUI client for MOOSE.'''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--input', '-i', type=str
        , required = False, help = 'Input file'
        )
    parser.add_argument('--server', '-s'
        , required = False, default = 'ghevar.ncbs.res.in:31417'
        , help = 'MOOSE Server'
        )
    class Args: pass 
    args = Args()
    parser.parse_args(namespace=args)
    main(vars(args))
