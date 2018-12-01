import pycurl
from io import BytesIO
from json import loads, dumps

class RapidReq():
	def __init__( self, statusCode, responseData ):
		self.status_code = statusCode
		self.responseData = responseData

	def json( self ):
		return loads( self.responseData )

def post( url, data = {}, headers = {} ):
	try:
		global requestURL
		request = pycurl.Curl()
		buff = BytesIO()
		request.setopt( pycurl.URL, url )
		request.setopt( pycurl.HTTPHEADER, [ "Content-Type: application/json" ] )
		request.setopt( pycurl.WRITEFUNCTION, buff.write )
		request.setopt( pycurl.POST, 1 )
		request.setopt( pycurl.POSTFIELDS, data )
		request.perform()
		responseData = buff.getvalue().decode( "UTF-8" )
		statusCode = request.getinfo( pycurl.HTTP_CODE )
		request.close()
		buff.close()
		return RapidReq( statusCode, responseData )
	except:
		return RapidReq( 418, "{ \"Error\" : \"I'm a teapot\" }" )