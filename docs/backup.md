# Backup

This page describes some suggestions to create a backup of your Linkding database.

## What to backup

All the data you need to backup are in the SQLite database.
So you only have to backup the contents of this database.

If you have installed Linkding using Docker, you can find the database in the `/etc/linkding/data` directory from the Docker container.

Below, we describe two methods to create a backup of the database.

- Create a copy of the SQLite databse with the SQLite backup function
- Create a plain textfile with the contents of the SQLite database with the SQLite dump function

Choose the method that fits you best.

## Using the SQLite backup function

With this method you create a new SQLite database, which is a copy of your linkding database.
This method uses the backup command in the [Command Line Shell For SQLite](https://sqlite.org/cli.html).
```shell
sqlite3 db.sqlite3 ".backup '$HOME/linkding.backup'"
```
After you have created the backup database `linkding.backup` you have to move it to another system, f.e., with rsync.

## Using the  SQLite dump function

With this method you create a plain text file with the SQL-statements to recreate the SQLite database.

```shell
sudo sqlite3 db.sqlite3 .dump > ~/bookmarks.sql
```

As this is a plain text file you can commit it any revision management system, like git.
When you use git, you can commit the changes, followed by a git push to a remote repository.


