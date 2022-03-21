# Syncify

Syncify is an easy to use command line program for synchronised Spotify sessions.

# Usage

Syncify has two modes: hosting and connecting.

## Host mode

You can host a session by using the `--host` flag when running the script,  the remote connect address is then shown on screen. Share the remote connect address with another user so they can use it with connect mode.

## Connect mode

You can connect to a session by using the `--connect <IP:port>` flag when running the script. **Note:** connecting to a session outside the local network will not work if the host hasn't port forwarded the port that the server listens on (default 35484). 


# TODO

* .ini file with configuration options like port to listen on, etc.
* Fix host mode keyboard interrupt not working, for now ctrl + break works
