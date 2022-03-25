# NetBox Migration Scripts

These scripts are offered to expedite the process of upgrading to a new major NetBox release. Unless otherwise noted, they are intended to be run on the version of NetBox immediately prior to that indicated in the module name. For example, scripts within the `netbox_v32_migration` module are meant to be run on NetBox v3.1.

To enable these scripts in your local NetBox instance, clone this repository and create symbolic links within your `SCRIPTS_ROOT` path to the desired module(s).

```
$ cd /opt/netbox/netbox/scripts
$ ln -s /path/to/repo/netbox_v32_migration.py
```

As it is impossible to anticipate every user's potential needs, these scripts are intended to serve as functional examples. Users who require advanced functionality are encouraged to modify these scripts to achieve the desired behavior.

