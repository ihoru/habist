# Habits + Todoist = Habist

## About

This is a FastAPI project (Python) with a set of webhooks for Todoist to mark/unmark custom tags in Exist.io by simply
marking tasks as done.

## Reason

I log habits in [Exist.io](https://exist.io/), but I also use [Todoist](https://todoist.io/) to have reminders about
these habits. Thus, I created these webhooks to sync marks about habits being done in Todoist to Exist.

## Commands

Use these commands by commenting a task in Todoist:

* `existio:TAGNAME` - to connect this task with a custom tag in Exist.io
* `existio:release` - to disconnect task from custom tag in Exist.io (or simply delete the task)
* `existio:yesterday` - to set this custom tag in Exist.io for yesterday
* `existio:on:YYYY-MM-DD` - to set this custom tag in Exist.io for custom date
* `existio:off:YYYY-MM-DD` - to UNset this custom tag in Exist.io for yesterday
* `existio:update` - force stats update

**To set custom tag for today, simply check task as done! ✅✅✅**

## Demo

After task connection with custom tag it will have comments with up-to-date statistics:

![](https://raw.githubusercontent.com/ihoru/habist/master/docs/images/todoist_task.png "Todoist task with Exist.io integration")

## Useful links

* https://developer.todoist.com/appconsole.html - to manage apps in Todoist
* https://exist.io/account/apps/ - manage apps in Exist.io

## Foreword

This project was created for my own needs and also to practice using FastAPI, but I decided to share it with the world.
If you are interested in using it for yourself contact me. Thanks!
