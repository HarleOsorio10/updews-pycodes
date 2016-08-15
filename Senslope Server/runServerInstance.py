import senslopeServer as server
import time, sys, gsmSerialio

debug = False

def main():
    network = sys.argv[1].upper()

    if network[0:5] not in ['GLOBE','SMART']:
        print ">> Error in network selection", network
        sys.exit()
    
    server.RunSenslopeServer(network)

if __name__ == '__main__':
    while True:
        try:
	        main()
        except KeyboardInterrupt:
            print 'Bye'
            break
    	except gsmSerialio.CustomGSMResetException:
    	    print "> Resetting system because of GSM failure"
    	    continue
        
