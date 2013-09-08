deploy:
	rm -rf output && ./newest-wok && rsync -vr output molly.cat:/srv/http/molly.cat
