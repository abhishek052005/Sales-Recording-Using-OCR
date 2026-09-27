const isLocalFrontend = ['localhost', '127.0.0.1'].includes(window.location.hostname);

window.API_BASE_URL = isLocalFrontend
	? 'http://127.0.0.1:8001'
	: 'https://YOUR-RENDER-SERVICE.onrender.com';