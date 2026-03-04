<div id="top"></div>
<br/>
<div align="center">
  
  <h2 align="center">🔄️ Discord Status Rotator</h2>

  <p align="center">
    This script allows you to change the status of your Discord account automatically from the statuses defined in a text file and extras.

    Please donnot claim this is your script. Made by Siebe. Problems? Dm me on discord: s_ieb_ee.
  </p>
</div>



---------------------------------------

---------------------------------------

---------------------------------------

### ⚙️ Configuration

- **token**: Your Discord token account.
- **status_sequence**: Rotate the status (online, dnd, idle, offline). You can have one fixed by removing the others and leaving only the one you want.
- **speed_rotator**: Time interval between each state change (in seconds).
- **emoji_config**: Controls when emojis change. Options are:
---------------------------------------

###  How to get your token (PC & Mobile Devices)

### - PC

1. Open your preferred browser (with developer tools) and login to [Discord](https://discord.com/app).
2. Press `CTRL + Shift + I` to open the Developer Tools and navigate to the Console tab.
3. Paste the following code into the Console and press Enter:
    ```javascript
    (webpackChunkdiscord_app.push([
        [""],
        {},
        (e) => {
            for (let t in ((m = []), e.c)) m.push(e.c[t]);
        },
    ]),
    m)
        .find((e) => e?.exports?.default?.getToken !== void 0)
        .exports.default.getToken();
    ```
4. The text that will be returned is enclosed in quotation marks and that will be YOUR token.


### - Mobile Devices

1. Open your browser 

2. Add a new bookmark (click the star icon ⭐ in the menu under the three dots).

3. Edit the bookmark name to Token Finder and set its URL with the following code:

   ```javascript
   javascript:(function () { location.reload(); var i = document.createElement("iframe"); document.body.appendChild(i); prompt("Token", i.contentWindow.localStorage.token.replace(/"/g, ""));})();
   ```
4. Visit [Discord](https://discord.com/app). and log in.

5. Click on the search bar, type Token Finder (do not press Enter or search).

6. Click on the bookmark you have named Token Finder.

7. A window will pop up with your Discord token, just copy it.


---------------------------------------

### 📃 Change History

```
- Made the script fully functional.
```

---------------------------------------


### 📞 Contact

You can contact me on Discord:
s_ieb_ee
