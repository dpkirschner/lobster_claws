LAUNCH_AGENTS := $(HOME)/Library/LaunchAgents
GOOGLE_AUTH_PLIST := launchd/com.lobsterclaws.google-auth.plist

.PHONY: install-google-auth reload-google-auth unload-google-auth

install-google-auth: $(GOOGLE_AUTH_PLIST)
	mkdir -p $(LAUNCH_AGENTS)
	mkdir -p $(HOME)/Library/Logs/lobsterclaws
	launchctl unload $(LAUNCH_AGENTS)/$$(basename $<) 2>/dev/null || true
	cp $< $(LAUNCH_AGENTS)/
	launchctl load $(LAUNCH_AGENTS)/$$(basename $<)
	@echo "Loaded $$(basename $<)"

unload-google-auth:
	launchctl unload $(LAUNCH_AGENTS)/$$(basename $(GOOGLE_AUTH_PLIST)) 2>/dev/null || true
	@echo "Unloaded $$(basename $(GOOGLE_AUTH_PLIST))"

reload-google-auth: install-google-auth
