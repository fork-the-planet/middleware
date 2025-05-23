#
# /etc/nscd.conf
#
# An example Name Service Cache config file.  This file is needed by nscd.
#
# WARNING: Running nscd with a secondary caching service like sssd may lead to
#          unexpected behaviour, especially with how long entries are cached.
#
# Legal entries are:
#
#	logfile			<file>
#	debug-level		<level>
#	threads			<initial #threads to use>
#	max-threads		<maximum #threads to use>
#	server-user             <user to run server as instead of root>
#		server-user is ignored if nscd is started with -S parameters
#       stat-user               <user who is allowed to request statistics>
#	reload-count		unlimited|<number>
#	paranoia		<yes|no>
#	restart-interval	<time in seconds>
#
#       enable-cache		<service> <yes|no>
#	positive-time-to-live	<service> <time in seconds>
#	negative-time-to-live   <service> <time in seconds>
#       suggested-size		<service> <prime number>
#	check-files		<service> <yes|no>
#	persistent		<service> <yes|no>
#	shared			<service> <yes|no>
#	NOTE: Setting 'shared' to a value of 'yes' will accelerate the lookup,
#	      but those lookups will not be counted as cache hits
#	      i.e. 'nscd -g' may show '0%'.
#	max-db-size		<service> <number bytes>
#	auto-propagate		<service> <yes|no>
#
# Currently supported cache names (services): passwd, group, hosts, services
# TrueNAS modification: enable for 'hosts' only
#
<%
    import os
    os.makedirs('/var/run/nscd/cache', mode=0o755, exist_ok=True)
%>\


#	logfile			/var/log/nscd.log
#	threads			4
#	max-threads		32
#	server-user		nobody
#	stat-user		somebody
	debug-level		0
#	reload-count		5
	paranoia		yes
	restart-interval	3600

	enable-cache		passwd		no
	positive-time-to-live	passwd		600
	negative-time-to-live	passwd		20
	suggested-size		passwd		211
	check-files		passwd		yes
	persistent		passwd		yes
	shared			passwd		yes
	max-db-size		passwd		33554432
	auto-propagate		passwd		yes

	enable-cache		group		no
	positive-time-to-live	group		3600
	negative-time-to-live	group		60
	suggested-size		group		211
	check-files		group		yes
	persistent		group		yes
	shared			group		yes
	max-db-size		group		33554432
	auto-propagate		group		yes

	enable-cache		hosts		yes
	positive-time-to-live	hosts		3600
	negative-time-to-live	hosts		20
	suggested-size		hosts		211
	check-files		hosts		yes
	persistent		hosts		yes
	shared			hosts		yes
	max-db-size		hosts		33554432

	enable-cache		services	no
	positive-time-to-live	services	28800
	negative-time-to-live	services	20
	suggested-size		services	211
	check-files		services	yes
	persistent		services	yes
	shared			services	yes
	max-db-size		services	33554432

	enable-cache		netgroup	no
	positive-time-to-live	netgroup	28800
	negative-time-to-live	netgroup	20
	suggested-size		netgroup	211
	check-files		netgroup	yes
	persistent		netgroup	yes
	shared			netgroup	yes
	max-db-size		netgroup	33554432
