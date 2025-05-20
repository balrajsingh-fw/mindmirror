MindMirror is a psychiatric assistant which provides readings of user's emotions and analyse user's voice to provide insights about their anxiety or depression.

For python 3.12.8 requirements file is requirements_old.txt
For python 3.10.1 requirements.txt is requirements file.

install python of preferred version and then run from root folder pip install -r requirements.txt or pip install -r requirements_old.txt. Then run the daphne command to execute asgi server for current python project.

Run the below command in terminal of root folder.
daphne -p 3002 -b 0.0.0.0 mindmirror.asgi:application
