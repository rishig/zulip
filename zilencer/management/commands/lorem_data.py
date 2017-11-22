lorem_words = """\
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Tortor posuere ac ut
consequat. Et netus et malesuada fames ac turpis. Tempus imperdiet nulla
malesuada pellentesque. Lorem ipsum dolor sit amet consectetur adipiscing
elit. Scelerisque eleifend donec pretium vulputate sapien nec. Ut consequat
semper viverra nam libero justo. Lobortis scelerisque fermentum dui faucibus
in. Lobortis scelerisque fermentum dui faucibus. Magna sit amet purus
gravida quis blandit turpis cursus. Nisl vel pretium lectus quam id leo in
vitae. Commodo nulla facilisi nullam vehicula ipsum a arcu cursus. Ligula
ullamcorper malesuada proin libero nunc consequat interdum varius sit. Eget
nunc lobortis mattis aliquam faucibus purus in massa. Auctor augue mauris
augue neque gravida. Commodo nulla facilisi nullam vehicula ipsum a arcu
cursus. Euismod in pellentesque massa placerat duis ultricies lacus sed
turpis. Mattis rhoncus urna neque viverra justo nec. Laoreet id donec
ultrices tincidunt arcu non. A erat nam at lectus urna. Morbi tristique
senectus et netus et malesuada fames ac. Nibh sit amet commodo nulla
facilisi nullam. Sapien pellentesque habitant morbi tristique
senectus. Viverra nam libero justo laoreet sit amet cursus sit amet. Enim
neque volutpat ac tincidunt vitae semper quis lectus. Odio aenean sed
adipiscing diam donec adipiscing tristique risus. Leo vel fringilla est
ullamcorper eget nulla facilisi. Ullamcorper eget nulla facilisi
etiam. Sodales neque sodales ut etiam sit amet nisl purus in. Nec feugiat in
fermentum posuere urna. Nunc aliquet bibendum enim facilisis gravida. Magnis
dis parturient montes nascetur ridiculus mus mauris vitae ultricies. Orci
porta non pulvinar neque laoreet suspendisse interdum consectetur
libero. Urna neque viverra justo nec ultrices dui sapien eget mi. Sociis
natoque penatibus et magnis dis parturient. Neque gravida in fermentum et
sollicitudin. Amet est placerat in egestas erat imperdiet sed. Neque egestas
congue quisque egestas. Viverra nam libero justo laoreet. Donec ultrices
tincidunt arcu non sodales neque sodales ut etiam. Sed egestas egestas
fringilla phasellus faucibus. Morbi blandit cursus risus at ultrices. Est
ullamcorper eget nulla facilisi etiam. Tincidunt praesent semper feugiat
nibh sed pulvinar. Amet porttitor eget dolor morbi non arcu risus. Dui ut
ornare lectus sit amet est placerat. Ultricies mi eget mauris pharetra et
ultrices neque ornare. Pretium fusce id velit ut tortor pretium
viverra. Convallis aenean et tortor at risus viverra adipiscing at. Libero
id faucibus nisl tincidunt eget. Sollicitudin ac orci phasellus egestas
tellus. Quisque id diam vel quam elementum pulvinar etiam non quam. Quisque
egestas diam in arcu cursus euismod. A iaculis at erat pellentesque
adipiscing commodo. Nullam eget felis eget nunc lobortis mattis
aliquam. Pellentesque elit ullamcorper dignissim cras tincidunt lobortis
feugiat vivamus at. Imperdiet proin fermentum leo vel orci porta non
pulvinar neque. Nullam ac tortor vitae purus faucibus ornare suspendisse
sed. Diam quam nulla porttitor massa id neque aliquam. Facilisi morbi tempus
iaculis urna id volutpat. Ridiculus mus mauris vitae ultricies leo integer
malesuada. Luctus accumsan tortor posuere ac ut consequat semper viverra
nam. Sit amet nisl suscipit adipiscing. Vulputate dignissim suspendisse in
est. Cursus sit amet dictum sit amet justo donec enim. Et leo duis ut diam
quam nulla porttitor. Pellentesque elit ullamcorper dignissim cras tincidunt
lobortis feugiat vivamus. Adipiscing elit ut aliquam purus sit amet. Sed sed
risus pretium quam vulputate dignissim suspendisse in. Dignissim cras
tincidunt lobortis feugiat. Rhoncus est pellentesque elit ullamcorper
dignissim. Eu ultrices vitae auctor eu augue ut lectus arcu bibendum. Sit
amet commodo nulla facilisi nullam vehicula ipsum a arcu. Facilisi cras
fermentum odio eu feugiat pretium nibh ipsum. Viverra vitae congue eu
consequat ac felis. Cursus in hac habitasse platea dictumst quisque sagittis
purus. Nunc mattis enim ut tellus elementum. Volutpat consequat mauris nunc
congue nisi vitae suscipit tellus mauris. Urna duis convallis convallis
tellus. Donec enim diam vulputate ut pharetra. Cursus turpis massa tincidunt
dui ut ornare lectus. Felis eget velit aliquet sagittis id consectetur
purus. Eros in cursus turpis massa tincidunt dui ut ornare. Diam ut
venenatis tellus in. Felis imperdiet proin fermentum leo vel orci
porta. Arcu risus quis varius quam quisque. Sit amet nisl suscipit
adipiscing bibendum est ultricies."""


lorem_words = lorem_words.replace('\n', ' ').split('. ')
lorem_words = [sentence + '.' for sentence in lorem_words if sentence]
