# Things that need to be done

- [x] Cleanup Post update
- [x] Implement feature update job.
- [x] Implement connection to elasticsearch
- [x] Build Docker images for all parts of the application
- [x] Deploy beta.rep0st.rene8888.at
- [x] Deploy to rep0st.rene8888.at
- [ ] Implement keyframe extraction for videos
- [ ] Implement video search
  
# Things that should be cleaned up
- [x] Feature update modules depends on Pr0grammAPIModule, meaning the app
      has to be started with command line flags for pr0gramm login.
- [ ] Allow webserver to be started in daemon mode if no persistent web apps are mounted.
      For example status pages should not keep the server alive if all other parts of the
      application are done.

# Nice to have
- [ ] Investigate usage of argparse configured through modules, to automatically
      inject command line arguments.
- [ ] Fix flag parsing error not being handled by logger
- [ ] Make logger injectable
- [ ] Make scheduler a decorator
