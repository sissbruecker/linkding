---
title: "Backups"
description: "How to back up your Linkding installation"
---

Linkding stores all data in the application's data folder.
The full path to that folder in the Docker container is `/etc/linkding/data`.
As described in the installation docs, you should mount the `/etc/linkding/data` folder to a folder on your host system.

The data folder contains the following contents that are relevant for backups:
- `db.sqlite3` - the SQLite database
- `assets` - folder that contains HTML snapshots of bookmarks
- `favicons` - folder that contains downloaded favicons
- `previews` - folder that contains downloaded preview images

The following sections explain how to back up the individual contents.

## Full backup

linkding provides a CLI command to create a full backup of the data folder. This creates a zip file that contains backups of the database, assets, favicons, and preview images.

:::note
This method assumes that you are using the default SQLite database.
If you are using a different database, such as Postgres, you'll have to back up the database and other contents of the data folder manually.
:::

To create a full backup, execute the following command:
```shell
docker exec -it linkding python manage.py full_backup /etc/linkding/data/backup.zip
```
This creates a `backup.zip` file in the Docker container under `/etc/linkding/data`.

To copy the backup file to your host system, execute the following command:
```shell
docker cp linkding:/etc/linkding/data/backup.zip backup.zip
```
This copies the backup file from the Docker container to the current folder on your host system.
Now you can move that file to your backup location.

To restore a backup: 
- Extract the zip file in a folder of your new installation.
- Rename the extracted folder to `data`.
- When starting the Docker container, mount that folder to `/etc/linkding/data` as explained in the README.
- Then start the Docker container.

## Alternative backup methods

If you can't use the full backup method, this section describes alternatives how to back up the individual contents of the data folder.

### SQLite database backup

linkding includes a CLI command for creating a backup copy of the database.

:::caution
While the SQLite database is just a single file, it is not recommended to just copy that file.
This method is not transaction safe and may result in a [corrupted database](https://www.sqlite.org/howtocorrupt.html).
Use one of the backup methods described below.
:::

:::caution
This method is deprecated and may be removed in the future.
Please use the full backup method described above.
:::

To create a backup, execute the following command:
```shell
docker exec -it linkding python manage.py backup /etc/linkding/data/backup.sqlite3
```
This creates a `backup.sqlite3` file in the Docker container under `/etc/linkding/data`.

To copy the backup file to your host system, execute the following command:
```shell
docker cp linkding:/etc/linkding/data/backup.sqlite3 backup.sqlite3
```
This copies the backup file from the Docker container to the current folder on your host system.
Now you can move that file to your backup location.

To restore the backup, just copy the backup file to the data folder of your new installation and rename it to `db.sqlite3`. Then start the Docker container.

### SQLite database SQL dump

Requires [SQLite](https://www.sqlite.org/index.html) to be installed on your host system.

With this method you create a plain text file with the SQL statements to recreate the SQLite database.
To create a backup, execute the following command in the data folder on your host system:
```shell
sqlite3 db.sqlite3 .dump > backup.sql
```
This creates a `backup.sql` which you can copy to your backup location.
As this is a plain text file you can also commit it to any revision management system, like git.
Using git, you can commit the changes, followed by a git push to a remote repository.

### Exporting bookmarks from the UI

This is the least technical option to back up bookmarks, but has several limitations:
- It does not export user profiles.
- It only exports your own bookmarks, not those of other users.
- It does not export URLs of snapshots on the Internet Archive Wayback machine.
- It does not export HTML snapshots of bookmarks. Even if you backup and restore the assets folder, the bookmarks will not be linked to the snapshots anymore.
- It does not export favicons or preview images.

Only use this method if you are fine with the above limitations.

To export bookmarks from the UI, open the general settings.
In the Export section, click on the *Download* button to download an HTML file containing all your bookmarks.
Then move that file to your backup location.

To restore bookmarks, open the general settings on your new installation.
In the Import section, click on the *Choose file* button to select the HTML file you downloaded before.
Then click on the *Import* button to import the bookmarks.

### Assets

If you are using the HTML snapshots feature, you should also do backups of the `assets` folder.
It contains the HTML snapshots files of your bookmarks which are referenced from the database.

To back up the assets, then you have to copy the `assets` folder to your backup location.

To restore the assets, copy the `assets` folder back to the data folder of your new installation.

### Favicons

Doing a backup of the icons is optional, as they can be downloaded again.

If you choose not to back up the icons, you can just restore the database and then click the _Refresh Favicons_ button in the general settings.
This will download all missing icons again.

If you want to back up the icons, then you have to copy the `favicons` folder to your backup location.

To restore the icons, copy the `favicons` folder back to the data folder of your new installation.
