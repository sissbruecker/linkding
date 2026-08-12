---
title: "Managed Hosting"
description: "Managed hosting options for linkding"
---

This section lists third-party services and platforms for hosting linkding, split by how much of the operation and maintenance they take care of for you.

A _managed service_ is the least technical option where the provider essentially just runs the app for you in a manner that you would expect any online app to work: you just register, start using the app, get automatic updates when available. _Hosting platforms_ are more generic in that they allow deploying arbitrary apps, which have a built-in template for linkding that makes that process easier for less technical users. Application updates require a manual redeployment, and managing the app might involve more technical details.

| Provider                                                                                                                                              | Type             | Updates   | Backups                                    | Regions |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|-----------|--------------------------------------------|---------|
| [PikaPods.com](https://www.pikapods.com/) <br> [1-click setup](https://www.pikapods.com/pods?run=linkding) | Managed service  | Automatic | Automated backups to S3 compatible buckets | EU, US  |
| [CloudBreak](https://cloudbreak.app/products/linkding/)                                                                                               | Managed service  | Automatic  | Unknown                                    | US      |
| [Hostim.dev](https://hostim.dev/) <br> [1-click setup](https://console.hostim.dev/dashboard?preview=1&modal=1&template=linkding)                                                                                                               | Hosting platform | Manual    | Custom through SSH access                  | EU      |

_Disclosure: PikaPods has a revenue sharing agreement with this project, sharing some of their revenue from hosting linkding instances._
