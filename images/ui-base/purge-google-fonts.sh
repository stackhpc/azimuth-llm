
SOURCE_CODE_PATH=/usr/local/lib/python3.11/site-packages/gradio/

# Strip out preconnect directives from HTML <link> tags
find $SOURCE_CODE_PATH -name "*.html" -type f -exec sed -i s!'rel="preconnect"'!!g {} \;

# Replace links with something harmless but identifiable
declare -a LINKS=("https://fonts.gstatic.com" "https://fonts.googleapis.com")
REPLACEMENT="no-google-fonts-here"
for item in "${LINKS[@]}"; do
    find $SOURCE_CODE_PATH -name "*.html" -type f -exec sed -i s!$item!$REPLACEMENT!g {} \;
done
