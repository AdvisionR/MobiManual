**MobiVisor Documentation System**

This document explains how MobiVisor web documentation is stored, generated, checked, and updated.

The main flow is:

Markdown  
   |  
   \+--\> HTML pages  
   |  
   \+--\> Combined HTML  
   |  
   \+--\> PDF

E2E / Protractor  
   |  
   \+--\> Documentation screenshots

# **1\. Documentation Files**

Web documentation is stored in language-specific folders:

public/doc/en/  
public/doc/tr/  
public/doc/de/

Most documentation content is written as Markdown.

For example:

public/doc/en/\_devices.md  
public/doc/en/\_apns.md  
public/doc/en/\_appinstallations.md

Screenshots are stored under:

public/doc/\<language\>/screenshots/

Example:

public/doc/en/screenshots/\_apn\_add\_form\_1.png

# **2\. Application Routes and Documentation**

Many documentation filenames follow the application's route structure.

This allows having documentation for each page in the system. Hence, the end user can check the documentation of the page he/she is in using this format.

For example, a route such as:

\#\!/devices

can have documentation such as:

\_devices.md

The project contains a script that compares application routes with \_\*.md documentation files.

During this comparison:

* route slashes are converted to underscores,  
* dynamic route parameters are converted to an id form,  
* the result is compared with Markdown filenames.

Therefore there is a route-to-documentation naming convention. We can use this knowledge to find out which pages have missing documentations using a script.

# **3\. Documentation Order**

The order of the combined documentation is defined manually in gruntfile.js.

It contains an array named:

htmlDocPages

For example:

var htmlDocPages \= \[  
    'cover\_page.md',  
    'chapter1.md',  
    '\_users.md',  
    '\_policies.md',  
    '\_devices.md',  
    '\_devicescommands.md',  
    '\_groups.md'  
\];

The order in this array becomes the order used in the combined documentation for both HTML and  PDF docs.

Therefore, when a new documentation page is created, it should also be added to htmlDocPages if we want to display it in the system manual.

# **4\. Generating HTML and PDF**

Documentation generation is handled by Grunt and Pandoc.

## **Individual HTML Pages**

Each Markdown file is converted into its own HTML file.

Conceptually:

page.md  \--\>  page.html

Pandoc performs the conversion.

## **Combined HTML**

Grunt also combines the files listed in htmlDocPages.

The result includes:

index.html  
combined.html

The combined HTML includes a Pandoc-generated table of contents and a search field to search the table of contents.

## **PDF**

The same ordered Markdown pages are also passed to Pandoc to create:

mobivisor.pdf

The simplified generation flow is:

htmlDocPages  
      |  
      \+--\> Pandoc \--\> index.html  
      |  
      \+--\> Pandoc \--\> combined.html  
      |  
      \+--\> Pandoc \--\> mobivisor.pdf

# **5\. Special Markdown Files**

Two Markdown files have special purposes.

## **search.md**

search.md is not a normal documentation page.

It is added while creating combined.html.

It provides:

* a Filter input,  
* filtering of the generated table of contents,  
* a link to mobivisor.pdf.

The search only filters entries in the Pandoc table of contents. It is not a full-text search of all documentation content.

## **break.md**

break.md contains:

\\pagebreak

Grunt inserts it between Markdown files while generating the PDF.

Its only purpose is to create page breaks in the PDF.

# **6\. Documentation Screenshots**

Note: This is subject to change. We were using our end-to-end tests for generating screenshots during the tests.   
This way the screenshots of the system would be up to date and changed regularly.  
However, we are changing our End-to-End test framework, hence we need to re-visit them and update them accordingly.

Screenshots are created through functions in helper.js.

The two important functions are:

helper.screenshot(fileName)  
helper.docshot(fileName)

## **screenshot()**

helper.screenshot() calls:

browser.takeScreenshot()

and writes the result into:

public/doc/\<language\>/screenshots/

## **Filename With an Explicit Name**

If a name is supplied:

helper.screenshot('apn\_add\_form')

the helper adds an underscore:

\_apn\_add\_form

It also adds a numeric index:

\_apn\_add\_form\_1.png  
\_apn\_add\_form\_2.png

## **Filename Without an Explicit Name**

If no filename is supplied, the current application URL is used.

The part after \\\#\! becomes the base filename.

For example:

\#\!/devices

can produce:

\_devices\_1.png

Route slashes are replaced by underscores.

## **Screenshot Language**

The language is read from:

SCREENSHOT\_LANGUAGE

If it is not set, English is used.

Therefore screenshots are written to paths such as:

public/doc/en/screenshots/  
public/doc/tr/screenshots/  
public/doc/de/screenshots/

## 6.1 docshot() vs screenshot()

The main difference is simple.

helper.screenshot(...)

creates the screenshot whenever the function is executed.

In contrast:

helper.docshot(...)

only creates the screenshot when:

NODE\_ENV \=== 'screenshot'

The README describes their intended usage as:

* use docshot() for screenshots needed only by documentation,  
* use screenshot() when the screenshot is also useful during testing.

The provided source does not contain an example E2E test using docshot(), so the exact preferred placement of these calls in test files is not shown here.

## 6.2 Screenshot Generation With Grunt

Developers normally run:

grunt screenshot\_en  
grunt screenshot\_tr  
grunt screenshot\_de

The language-specific task calls the common screenshot process.

At a high level the process is:

1\. back up existing screenshots,

2\. start MobiVisor in screenshot mode,

3\. prepare E2E data,

4\. run Protractor,

5\. create screenshots,

6\. remove unnecessary screenshot files,

7\. keep screenshots referenced by Markdown,

8\. crop the images,

9\. minimize the PNG files,

10\. merge useful existing screenshots back,

11\. remove unreferenced screenshots again.

Image processing uses external tools including ImageMagick and pngquant.

## 6.3 screenshot\_protractor.js

The screenshot Protractor configuration also uses:

protractor-screenshot-reporter

Its output directory is also language-specific:

public/doc/\<language\>/screenshots

However, this reporter and helper.screenshot() are two separate screenshot mechanisms.

The reporter creates filenames based on Jasmine test descriptions.

The helper creates filenames from either:

* an explicitly supplied filename, or  
* the current application URL.

They should therefore not be treated as the same mechanism.

## 6.4 Using Screenshots in Markdown

Screenshots are referenced using normal Markdown syntax.

For example:

\!\[\](screenshots/\_apn\_add\_form\_1.png)

or:

\!\[\](screenshots/devices\_page-should\_filter\_by\_user.png)

Some documentation also uses normal images from the img directory:

\!\[\](img/commands\_for\_ios\_devices.png)

Therefore, not every image in the documentation is generated by the screenshot system.

# **7\. Checking Missing Documentation**

The project provides:

grunt check-missing-doc

This performs two useful checks.

First, application routes are compared with \_\*.md documentation files.

Second, existing Markdown files are compared with the htmlDocPages list.

This can detect cases such as:

* a route with no corresponding documentation file,  
* a documentation file not included in the combined documentation,  
* an entry in htmlDocPages whose Markdown file is missing.

search.md and break.md are excluded from the normal page comparison because they are special files.

# **8\. Main Developer Commands**

The most important commands for web documentation are:

grunt screenshot\_en  
grunt screenshot\_tr  
grunt screenshot\_de

grunt web\_docs

grunt check-missing-doc

In normal usage:

* screenshot\_\* recreates documentation screenshots,  
* web\_docs regenerates HTML and PDF documentation,  
* check-missing-doc checks documentation completeness.

# **9\. Adding a New Documentation Page**

A simple workflow for adding a new page is:

1\. Create the Markdown file for each required language.

public/doc/en/\_newPage.md  
public/doc/tr/\_newPage.md  
public/doc/de/\_newPage.md

2\. If it should appear in the combined documentation, add it to htmlDocPages in the correct position.

3\. Add documentation screenshot calls to the relevant E2E flow when screenshots are needed.

helper.docshot('new\_page')

4\. Reference the generated image from Markdown.

\!\[\](screenshots/\_new\_page\_1.png)

5\. Regenerate the required screenshots.

grunt screenshot\_en

6\. Regenerate the documentation.

grunt web\_docs

7\. Check for missing or unregistered documentation.

grunt check-missing-doc

# **10\. Overall Flow**

The complete documented flow can be summarized as:

Application / E2E  
       |  
       | docshot() / screenshot()  
       v  
Documentation Screenshots  
       |  
       v  
Markdown Files  
       |  
       | htmlDocPages defines order  
       v  
      Pandoc  
     /   |   \\  
    /    |    \\  
 HTML Combined PDF  
       HTML

Grunt coordinates screenshot generation, documentation generation, image processing, and completeness checks.

Two details require additional project source for a complete end-to-end description:

* how the running MobiVisor UI selects and opens documentation for the current route,  
* where helper.docshot() calls are normally placed in the E2E test source.

Everything else in this document is directly supported by the provided documentation, Grunt configuration, screenshot helper, and checking scripts.

