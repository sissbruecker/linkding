# Backups

This page describes some options on how to create backups.

## What to backup

Linkding stores all data in a SQLite database, so all you need to backup are the contents of that database.

The location of the database file is `data/db.sqlite3` in the application folder. 
If you are using Docker then the full path in the Docker container is `/etc/linkding/data/db.sqlite`. 
As described in the installation docs, you should mount the `/etc/linkding/data` folder to a folder on your host system, from which you then can execute the backup.

Below, we describe several methods to create a backup of the database:

- Manual backup using the export function from the UI
- Create a copy of the SQLite database with the SQLite backup function
- Create a plain textfile with the contents of the SQLite database with the SQLite dump function

Choose the method that fits you best.

## Exporting from the UI

The least technical option is to use the bookmark export in the UI.
Go to the settings page and open the *Data* tab. 
Then click on the *Download* button to download an HTML file containing all your bookmarks.
You can backup this file on a drive, or an online file host.

## Using the SQLite backup function

Requires [SQLite](https://www.sqlite.org/index.html) to be installed on your host system.

With this method you create a new SQLite database, which is a copy of your linkding database.
This method uses the backup command in the [Command Line Shell For SQLite](https://sqlite.org/cli.html).
```shell
sqlite3 db.sqlite3 ".backup 'backup.sqlite3'"
```
After you have created the backup database `backup.sqlite` you have to move it to another system, for example with rsync.

## Using the SQLite dump function

Requires [SQLite](https://www.sqlite.org/index.html) to be installed on your host system.

With this method you create a plain text file with the SQL statements to recreate the SQLite database.

```shell
sqlite3 db.sqlite3 .dump > backup.sql
```

As this is a plain text file you can commit it to any revision management system, like git.
Using git you can commit the changes, followed by a git push to a remote repository.


