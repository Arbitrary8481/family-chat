// Global state
let socket;
let currentUser = null;

function getStoredChannel() {
    // Only trust a stored channel if it still actually exists — an admin
    // may have deleted it since it was last saved.
    try {
        const stored = localStorage.getItem('lastChannel');
        if (stored && document.querySelector(`.channel[data-channel="${CSS.escape(stored)}"]`)) {
            return stored;
        }
    } catch (e) {}
    return null;
}

let currentChannel = getStoredChannel() || window.DEFAULT_CHANNEL || 'general';
let selectedFile = null;
let customEmojis = {};
let recentEmojis = JSON.parse(localStorage.getItem('recentEmojis') || '[]');
// Which emoji tab is currently selected — restored when a search is
// cleared, since a search temporarily takes over the grid regardless of
// which tab is active.
let currentEmojiCategory = 'recent';
// Which message (if any) the emoji picker is currently choosing a
// reaction for. null means it's in its normal "insert into the
// composer" mode. Set by openReactionPicker(), cleared whenever the
// picker closes.
let emojiPickerContext = null;

// Standard emoji categories
const emojiCategories = {
    people: ['😀','😃','😄','😁','😅','😂','🤣','😊','😇','🙂','🙃','😉','😌','😍','🥰','😘','😗','😙','😚','😋','😛','😝','😜','🤪','🤨','🧐','🤓','😎','🥸','🤩','🥳','😏','😒','😞','😔','😟','😕','🙁','☹️','😣','😖','😫','😩','🥺','😢','😭','😤','😠','😡','🤬','🤯','😳','🥵','🥶','😱','😨','😰','😥','😓','🤗','🤔','🤭','🤫','🤥','😶','😐','😑','😬','🙄','😯','😦','😧','😮','😲','🥱','😴','🤤','😪','😵','🤐','🥴','🤢','🤮','🤧','😷','🤒','🤕','🤑','🤠','😈','👿','👹','👺','🤡','💩','👻','💀','☠️','👽','👾','🤖','🎃','😺','😸','😹','😻','😼','😽','🙀','😿','😾','🤲','👐','🙌','👏','🤝','👍','👎','👊','✊','🤛','🤜','🤞','✌️','🤟','🤘','👌','🤏','👈','👉','👆','👇','☝️','✋','🤚','🖐️','🖖','👋','🤙','💪','🦾','🖕','✍️','🙏','🦶','🦵','🦿','💄','💋','👄','🦷','👅','👂','🦻','👃','👣','👁️','👀','🧠','🫀','🫁','🦴','🦷','👀','💯'],
    nature: ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐽','🐸','🐵','🙈','🙉','🙊','🐒','🐔','🐧','🐦','🐤','🐣','🐥','🦆','🦅','🦉','🦇','🐺','🐗','🐴','🦄','🐝','🐛','🦋','🐌','🐞','🐜','🦟','🦗','🕷️','🕸️','🦂','🐢','🐍','🦎','🦖','🦕','🐙','🦑','🦐','🦞','🦀','🐡','🐠','🐟','🐬','🐳','🐋','🦈','🐊','🐅','🐆','🦓','🦍','🦧','🐘','🦛','🦏','🐪','🐫','🦒','🦘','🐃','🐂','🐄','🐎','🐖','🐏','🐑','🦙','🐐','🦌','🐕','🐩','🦮','🐕‍🦺','🐈','🐈‍⬛','🐓','🦃','🦚','🦜','🦢','🦩','🕊️','🐇','🦝','🦨','🦡','🦦','🦥','🐁','🐀','🐿️','🦔','🐾','🐉','🐲','🌵','🎄','🌲','🌳','🌴','🌱','🌿','☘️','🍀','🎍','🎋','🍃','🍂','🍁','🍄','🐚','🌾','💐','🌷','🌹','🥀','🌺','🌸','🌼','🌻','🌞','🌝','🌛','🌜','🌚','🌕','🌖','🌗','🌘','🌑','🌒','🌓','🌔','🌙','🌎','🌍','🌏','🪐','💫','⭐','🌟','✨','⚡','🔥','💥','☄️','☀️','🌤️','⛅','🌥️','🌦️','🌈','☁️','🌧️','⛈️','🌩️','🌨️','❄️','☃️','⛄','🌬️','💨','💧','💦','☔','☂️','🌊','🌫️'],
    food: ['🍏','🍎','🍐','🍊','🍋','🍌','🍉','🍇','🍓','🍈','🍒','🍑','🍍','🥝','🥥','🥑','🍆','🍅','🌶️','🥒','🥬','🥦','🧄','🧅','🍄','🥜','🌰','🍞','🥐','🥖','🥨','🥯','🥞','🧇','🧀','🍖','🍗','🥩','🥓','🍔','🍟','🍕','🌭','🥪','🌮','🌯','🥙','🧆','🥚','🍳','🥘','🍲','🥣','🥗','🍿','🧈','🧂','🥫','🍱','🍘','🍙','🍚','🍛','🍜','🍝','🍠','🍢','🍣','🍤','🍥','🍡','🍦','🍧','🍨','🍩','🍪','🎂','🍰','🧁','🥧','🍫','🍬','🍭','🍮','🍯','🍼','🥛','☕','🍵','🧃','🥤','🍶','🍺','🍻','🥂','🍷','🥃','🍸','🍹','🧉','🍾','🧊','🥄','🍴','🍽️','🥣','🥡','🥢','🧂'],
    activities: ['⚽','🏀','🏈','⚾','🥎','🎾','🏐','🏉','🥏','🎱','🪀','🏓','🏸','🏒','🏑','🥍','🏏','🥅','⛳','🪁','🏹','🎣','🤿','🥊','🥋','🎽','🛹','🛷','⛸️','🥌','🎿','⛷️','🏂','🏋️','🤼','🤽','🤾','🤺','🏇','⛷️','🏂','🏌️','🏄','🚣','🏊','⛹️','🏋️','🚴','🚵','🎽','🎿','🛷','🥅','⛳','🎣','🎽','🎿','🎯','🎱','🔮','🧿','🎮','🕹️','🎰','🎲','🧩','🧸','🪅','🪆','♠️','♥️','♦️','♣️','♟️','🃏','🀄','🎴','🎭','🖼️','🎨','🧵','🧶','🥼','🥽','🥾','🥿','👟','👞','🥾','🥿','👠','👡','👢','👑','👒','🎩','🎓','🧢','⛑️','📿','💄','💍','💎','🔇','🔈','🔉','🔊','📢','📣','📯','🔔','🔕','🎼','🎵','🎶','🎙️','🎚️','🎛️','🎤','🎧','📻','🎷','🎸','🎹','🎺','🎻','🪕','🥁','📱','📲','☎️','📞','📟','📠','🔋','🔌','💻','🖥️','🖨️','⌨️','🖱️','🖲️','💽','💾','💿','📀','🧮','🎥','🎞️','📽️','🎬','📺','📷','📸','📹','📼','🔍','🔎','🕯️','💡','🔦','🏮','🪔','📔','📕','📖','📗','📘','📙','📚','📓','📒','📃','📜','📄','📰','🗞️','📑','🔖','🏷️','💰','🪙','💴','💵','💶','💷','💸','💳','🧾','💹','✉️','📧','📨','📩','📤','📥','📦','📫','📪','📬','📭','📮','🗳️','✏️','✒️','🖋️','🖊️','🖌️','🖍️','📝','💼','📁','📂','🗂️','📅','📆','🗒️','🗓️','📇','📈','📉','📊','📋','📌','📍','📎','🖇️','📏','📐','✂️','🗃️','🗄️','🗑️','🔒','🔓','🔏','🔐','🔑','🗝️','🔨','🪓','⛏️','⚒️','🛠️','🗡️','⚔️','🔫','🏹','🛡️','🔧','🔩','⚙️','🗜️','⚖️','🦯','🔗','⛓️','🧰','🧲','🧪','🧫','🧬','🔬','🔭','📡','💉','🩸','💊','🩹','🩺','🌡️','🚽','🚰','🚿','🛁','🛀','🧴','🧷','🧹','🧺','🧻','🧼','🧽','🧯','🛒','🚬','⚰️','⚱️','🗿','🚂','🚃','🚄','🚅','🚆','🚇','🚈','🚉','🚊','🚝','🚞','🚋','🚌','🚍','🚎','🚐','🚑','🚒','🚓','🚔','🚕','🚖','🚗','🚘','🚙','🚚','🚛','🚜','🏎️','🏍️','🛵','🦽','🦼','🛺','🚲','🛴','🛹','🛼','🚏','🛣️','🛤️','🛢️','⛽','🚨','🚥','🚦','🛑','🚧','⚓','⛵','🛶','🚤','🛳️','⛴️','🚢','✈️','🛩️','🛫','🛬','🪂','💺','🚁','🚟','🚠','🚡','🛰️','🚀','🛸','🛎️','🧳','⌛','⏳','⌚','⏰','⏱️','⏲️','🕰️','🕛','🕧','🕐','🕜','🕑','🕝','🕒','🕞','🕓','🕟','🕔','🕠','🕕','🕡','🕖','🕢','🕗','🕣','🕘','🕤','🕙','🕥','🕚','🕦','🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘','🌙','🌚','🌛','🌜','🌡️','☀️','🌝','🌞','🪐','⭐','🌟','🌠','🌌','☁️','⛅','⛈️','🌤️','🌥️','🌦️','🌧️','🌨️','🌩️','🌪️','🌫️','🌬️','🌀','🌈','🌂','☂️','☔','⛱️','⚡','❄️','☃️','⛄','☄️','🔥','💧','🌊']
};

// Searchable names for the unicode emoji above (generated from the
// `emoji` Python package's canonical CLDR short names), so the search
// box has something meaningful to match against — the raw characters
// themselves obviously aren't searchable text.
const emojiNames = {
'😀':'grinning face','😃':'grinning face with big eyes','😄':'grinning face with smiling eyes','😁':'beaming face with smiling eyes','😅':'grinning face with sweat','😂':'face with tears of joy','🤣':'rolling on the floor laughing','😊':'smiling face with smiling eyes','😇':'smiling face with halo','🙂':'slightly smiling face','🙃':'upside-down face','😉':'winking face','😌':'relieved face','😍':'smiling face with heart-eyes','🥰':'smiling face with hearts','😘':'face blowing a kiss','😗':'kissing face',
'😙':'kissing face with smiling eyes','😚':'kissing face with closed eyes','😋':'face savoring food','😛':'face with tongue','😝':'squinting face with tongue','😜':'winking face with tongue','🤪':'zany face','🤨':'face with raised eyebrow','🧐':'face with monocle','🤓':'nerd face','😎':'smiling face with sunglasses','🥸':'disguised face','🤩':'star-struck','🥳':'partying face','😏':'smirking face','😒':'unamused face','😞':'disappointed face','😔':'pensive face','😟':'worried face','😕':'confused face',
'🙁':'slightly frowning face','☹️':'frowning face','😣':'persevering face','😖':'confounded face','😫':'tired face','😩':'weary face','🥺':'pleading face','😢':'crying face','😭':'loudly crying face','😤':'face with steam from nose','😠':'angry face','😡':'enraged face','🤬':'face with symbols on mouth','🤯':'exploding head','😳':'flushed face','🥵':'hot face','🥶':'cold face','😱':'face screaming in fear','😨':'fearful face','😰':'anxious face with sweat','😥':'sad but relieved face','😓':'downcast face with sweat',
'🤗':'smiling face with open hands','🤔':'thinking face','🤭':'face with hand over mouth','🤫':'shushing face','🤥':'lying face','😶':'face without mouth','😐':'neutral face','😑':'expressionless face','😬':'grimacing face','🙄':'face with rolling eyes','😯':'hushed face','😦':'frowning face with open mouth','😧':'anguished face','😮':'face with open mouth','😲':'astonished face','🥱':'yawning face','😴':'sleeping face','🤤':'drooling face','😪':'sleepy face','😵':'face with crossed-out eyes','🤐':'zipper-mouth face',
'🥴':'woozy face','🤢':'nauseated face','🤮':'face vomiting','🤧':'sneezing face','😷':'face with medical mask','🤒':'face with thermometer','🤕':'face with head-bandage','🤑':'money-mouth face','🤠':'cowboy hat face','😈':'smiling face with horns','👿':'angry face with horns','👹':'ogre','👺':'goblin','🤡':'clown face','💩':'pile of poo','👻':'ghost','💀':'skull','☠️':'skull and crossbones','👽':'alien','👾':'alien monster','🤖':'robot','🎃':'jack-o-lantern','😺':'grinning cat','😸':'grinning cat with smiling eyes',
'😹':'cat with tears of joy','😻':'smiling cat with heart-eyes','😼':'cat with wry smile','😽':'kissing cat','🙀':'weary cat','😿':'crying cat','😾':'pouting cat','🤲':'palms up together','👐':'open hands','🙌':'raising hands','👏':'clapping hands','🤝':'handshake','👍':'thumbs up','👎':'thumbs down','👊':'oncoming fist','✊':'raised fist','🤛':'left-facing fist','🤜':'right-facing fist','🤞':'crossed fingers','✌️':'victory hand','🤟':'love-you gesture','🤘':'sign of the horns','👌':'OK hand','🤏':'pinching hand',
'👈':'backhand index pointing left','👉':'backhand index pointing right','👆':'backhand index pointing up','👇':'backhand index pointing down','☝️':'index pointing up','✋':'raised hand','🤚':'raised back of hand','🖐️':'hand with fingers splayed','🖖':'vulcan salute','👋':'waving hand','🤙':'call me hand','💪':'flexed biceps','🦾':'mechanical arm','🖕':'middle finger','✍️':'writing hand','🙏':'folded hands','🦶':'foot','🦵':'leg','🦿':'mechanical leg','💄':'lipstick','💋':'kiss mark','👄':'mouth',
'🦷':'tooth','👅':'tongue','👂':'ear','🦻':'ear with hearing aid','👃':'nose','👣':'footprints','👁️':'eye','👀':'eyes','🧠':'brain','🫀':'anatomical heart','🫁':'lungs','🦴':'bone','🐶':'dog face','🐱':'cat face','🐭':'mouse face','🐹':'hamster','🐰':'rabbit face','🦊':'fox','🐻':'bear','🐼':'panda','🐨':'koala','🐯':'tiger face','🦁':'lion','🐮':'cow face','🐷':'pig face','🐽':'pig nose','🐸':'frog','🐵':'monkey face','🙈':'see-no-evil monkey','🙉':'hear-no-evil monkey','🙊':'speak-no-evil monkey',
'🐒':'monkey','🐔':'chicken','🐧':'penguin','🐦':'bird','🐤':'baby chick','🐣':'hatching chick','🐥':'front-facing baby chick','🦆':'duck','🦅':'eagle','🦉':'owl','🦇':'bat','🐺':'wolf','🐗':'boar','🐴':'horse face','🦄':'unicorn','🐝':'honeybee','🐛':'bug','🦋':'butterfly','🐌':'snail','🐞':'lady beetle','🐜':'ant','🦟':'mosquito','🦗':'cricket','🕷️':'spider','🕸️':'spider web','🦂':'scorpion','🐢':'turtle','🐍':'snake','🦎':'lizard','🦖':'T-Rex','🦕':'sauropod','🐙':'octopus','🦑':'squid','🦐':'shrimp',
'🦞':'lobster','🦀':'crab','🐡':'blowfish','🐠':'tropical fish','🐟':'fish','🐬':'dolphin','🐳':'spouting whale','🐋':'whale','🦈':'shark','🐊':'crocodile','🐅':'tiger','🐆':'leopard','🦓':'zebra','🦍':'gorilla','🦧':'orangutan','🐘':'elephant','🦛':'hippopotamus','🦏':'rhinoceros','🐪':'camel','🐫':'two-hump camel','🦒':'giraffe','🦘':'kangaroo','🐃':'water buffalo','🐂':'ox','🐄':'cow','🐎':'horse','🐖':'pig','🐏':'ram','🐑':'ewe','🦙':'llama','🐐':'goat','🦌':'deer','🐕':'dog','🐩':'poodle','🦮':'guide dog',
'🐕‍🦺':'service dog','🐈':'cat','🐈‍⬛':'black cat','🐓':'rooster','🦃':'turkey','🦚':'peacock','🦜':'parrot','🦢':'swan','🦩':'flamingo','🕊️':'dove','🐇':'rabbit','🦝':'raccoon','🦨':'skunk','🦡':'badger','🦦':'otter','🦥':'sloth','🐁':'mouse','🐀':'rat','🐿️':'chipmunk','🦔':'hedgehog','🐾':'paw prints','🐉':'dragon','🐲':'dragon face','🌵':'cactus','🎄':'Christmas tree','🌲':'evergreen tree','🌳':'deciduous tree','🌴':'palm tree','🌱':'seedling','🌿':'herb','☘️':'shamrock','🍀':'four leaf clover',
'🎍':'pine decoration','🎋':'tanabata tree','🍃':'leaf fluttering in wind','🍂':'fallen leaf','🍁':'maple leaf','🍄':'mushroom','🐚':'spiral shell','🌾':'sheaf of rice','💐':'bouquet','🌷':'tulip','🌹':'rose','🥀':'wilted flower','🌺':'hibiscus','🌸':'cherry blossom','🌼':'blossom','🌻':'sunflower','🌞':'sun with face','🌝':'full moon face','🌛':'first quarter moon face','🌜':'last quarter moon face','🌚':'new moon face','🌕':'full moon','🌖':'waning gibbous moon','🌗':'last quarter moon','🌘':'waning crescent moon',
'🌑':'new moon','🌒':'waxing crescent moon','🌓':'first quarter moon','🌔':'waxing gibbous moon','🌙':'crescent moon','🌎':'globe showing Americas','🌍':'globe showing Europe-Africa','🌏':'globe showing Asia-Australia','🪐':'ringed planet','💫':'dizzy','⭐':'star','🌟':'glowing star','✨':'sparkles','⚡':'high voltage','🔥':'fire','💥':'collision','☄️':'comet','☀️':'sun','🌤️':'sun behind small cloud','⛅':'sun behind cloud','🌥️':'sun behind large cloud','🌦️':'sun behind rain cloud','🌈':'rainbow',
'☁️':'cloud','🌧️':'cloud with rain','⛈️':'cloud with lightning and rain','🌩️':'cloud with lightning','🌨️':'cloud with snow','❄️':'snowflake','☃️':'snowman','⛄':'snowman without snow','🌬️':'wind face','💨':'dashing away','💧':'droplet','💦':'sweat droplets','☔':'umbrella with rain drops','☂️':'umbrella','🌊':'water wave','🌫️':'fog','🍏':'green apple','🍎':'red apple','🍐':'pear','🍊':'tangerine','🍋':'lemon','🍌':'banana','🍉':'watermelon','🍇':'grapes','🍓':'strawberry','🍈':'melon','🍒':'cherries',
'🍑':'peach','🍍':'pineapple','🥝':'kiwi fruit','🥥':'coconut','🥑':'avocado','🍆':'eggplant','🍅':'tomato','🌶️':'hot pepper','🥒':'cucumber','🥬':'leafy green','🥦':'broccoli','🧄':'garlic','🧅':'onion','🥜':'peanuts','🌰':'chestnut','🍞':'bread','🥐':'croissant','🥖':'baguette bread','🥨':'pretzel','🥯':'bagel','🥞':'pancakes','🧇':'waffle','🧀':'cheese wedge','🍖':'meat on bone','🍗':'poultry leg','🥩':'cut of meat','🥓':'bacon','🍔':'hamburger','🍟':'french fries','🍕':'pizza','🌭':'hot dog',
'🥪':'sandwich','🌮':'taco','🌯':'burrito','🥙':'stuffed flatbread','🧆':'falafel','🥚':'egg','🍳':'cooking','🥘':'shallow pan of food','🍲':'pot of food','🥣':'bowl with spoon','🥗':'green salad','🍿':'popcorn','🧈':'butter','🧂':'salt','🥫':'canned food','🍱':'bento box','🍘':'rice cracker','🍙':'rice ball','🍚':'cooked rice','🍛':'curry rice','🍜':'steaming bowl','🍝':'spaghetti','🍠':'roasted sweet potato','🍢':'oden','🍣':'sushi','🍤':'fried shrimp','🍥':'fish cake with swirl','🍡':'dango','🍦':'soft ice cream',
'🍧':'shaved ice','🍨':'ice cream','🍩':'doughnut','🍪':'cookie','🎂':'birthday cake','🍰':'shortcake','🧁':'cupcake','🥧':'pie','🍫':'chocolate bar','🍬':'candy','🍭':'lollipop','🍮':'custard','🍯':'honey pot','🍼':'baby bottle','🥛':'glass of milk','☕':'hot beverage','🍵':'teacup without handle','🧃':'beverage box','🥤':'cup with straw','🍶':'sake','🍺':'beer mug','🍻':'clinking beer mugs','🥂':'clinking glasses','🍷':'wine glass','🥃':'tumbler glass','🍸':'cocktail glass','🍹':'tropical drink',
'🧉':'mate','🍾':'bottle with popping cork','🧊':'ice','🥄':'spoon','🍴':'fork and knife','🍽️':'fork and knife with plate','🥡':'takeout box','🥢':'chopsticks','⚽':'soccer ball','🏀':'basketball','🏈':'american football','⚾':'baseball','🥎':'softball','🎾':'tennis','🏐':'volleyball','🏉':'rugby football','🥏':'flying disc','🎱':'pool 8 ball','🪀':'yo-yo','🏓':'ping pong','🏸':'badminton','🏒':'ice hockey','🏑':'field hockey','🥍':'lacrosse','🏏':'cricket game','🥅':'goal net','⛳':'flag in hole',
'🪁':'kite','🏹':'bow and arrow','🎣':'fishing pole','🤿':'diving mask','🥊':'boxing glove','🥋':'martial arts uniform','🎽':'running shirt','🛹':'skateboard','🛷':'sled','⛸️':'ice skate','🥌':'curling stone','🎿':'skis','⛷️':'skier','🏂':'snowboarder','🏋️':'person lifting weights','🤼':'people wrestling','🤽':'person playing water polo','🤾':'person playing handball','🤺':'person fencing','🏇':'horse racing','🏌️':'person golfing','🏄':'person surfing','🚣':'person rowing boat','🏊':'person swimming',
'⛹️':'person bouncing ball','🚴':'person biking','🚵':'person mountain biking','🎯':'bullseye','🔮':'crystal ball','🧿':'nazar amulet','🎮':'video game','🕹️':'joystick','🎰':'slot machine','🎲':'game die','🧩':'puzzle piece','🧸':'teddy bear','🪅':'piñata','🪆':'nesting dolls','♠️':'spade suit','♥️':'heart suit','♦️':'diamond suit','♣️':'club suit','♟️':'chess pawn','🃏':'joker','🀄':'mahjong red dragon','🎴':'flower playing cards','🎭':'performing arts','🖼️':'framed picture','🎨':'artist palette',
'🧵':'thread','🧶':'yarn','🥼':'lab coat','🥽':'goggles','🥾':'hiking boot','🥿':'flat shoe','👟':'running shoe','👞':'man’s shoe','👠':'high-heeled shoe','👡':'woman’s sandal','👢':'woman’s boot','👑':'crown','👒':'woman’s hat','🎩':'top hat','🎓':'graduation cap','🧢':'billed cap','⛑️':'rescue worker’s helmet','📿':'prayer beads','💍':'ring','💎':'gem stone','🔇':'muted speaker','🔈':'speaker low volume','🔉':'speaker medium volume','🔊':'speaker high volume','📢':'loudspeaker','📣':'megaphone',
'📯':'postal horn','🔔':'bell','🔕':'bell with slash','🎼':'musical score','🎵':'musical note','🎶':'musical notes','🎙️':'studio microphone','🎚️':'level slider','🎛️':'control knobs','🎤':'microphone','🎧':'headphone','📻':'radio','🎷':'saxophone','🎸':'guitar','🎹':'musical keyboard','🎺':'trumpet','🎻':'violin','🪕':'banjo','🥁':'drum','📱':'mobile phone','📲':'mobile phone with arrow','☎️':'telephone','📞':'telephone receiver','📟':'pager','📠':'fax machine','🔋':'battery','🔌':'electric plug',
'💻':'laptop','🖥️':'desktop computer','🖨️':'printer','⌨️':'keyboard','🖱️':'computer mouse','🖲️':'trackball','💽':'computer disk','💾':'floppy disk','💿':'optical disk','📀':'dvd','🧮':'abacus','🎥':'movie camera','🎞️':'film frames','📽️':'film projector','🎬':'clapper board','📺':'television','📷':'camera','📸':'camera with flash','📹':'video camera','📼':'videocassette','🔍':'magnifying glass tilted left','🔎':'magnifying glass tilted right','🕯️':'candle','💡':'light bulb','🔦':'flashlight',
'🏮':'red paper lantern','🪔':'diya lamp','📔':'notebook with decorative cover','📕':'closed book','📖':'open book','📗':'green book','📘':'blue book','📙':'orange book','📚':'books','📓':'notebook','📒':'ledger','📃':'page with curl','📜':'scroll','📄':'page facing up','📰':'newspaper','🗞️':'rolled-up newspaper','📑':'bookmark tabs','🔖':'bookmark','🏷️':'label','💰':'money bag','🪙':'coin','💴':'yen banknote','💵':'dollar banknote','💶':'euro banknote','💷':'pound banknote','💸':'money with wings',
'💳':'credit card','🧾':'receipt','💹':'chart increasing with yen','✉️':'envelope','📧':'e-mail','📨':'incoming envelope','📩':'envelope with arrow','📤':'outbox tray','📥':'inbox tray','📦':'package','📫':'closed mailbox with raised flag','📪':'closed mailbox with lowered flag','📬':'open mailbox with raised flag','📭':'open mailbox with lowered flag','📮':'postbox','🗳️':'ballot box with ballot','✏️':'pencil','✒️':'black nib','🖋️':'fountain pen','🖊️':'pen','🖌️':'paintbrush','🖍️':'crayon',
'📝':'memo','💼':'briefcase','📁':'file folder','📂':'open file folder','🗂️':'card index dividers','📅':'calendar','📆':'tear-off calendar','🗒️':'spiral notepad','🗓️':'spiral calendar','📇':'card index','📈':'chart increasing','📉':'chart decreasing','📊':'bar chart','📋':'clipboard','📌':'pushpin','📍':'round pushpin','📎':'paperclip','🖇️':'linked paperclips','📏':'straight ruler','📐':'triangular ruler','✂️':'scissors','🗃️':'card file box','🗄️':'file cabinet','🗑️':'wastebasket','🔒':'locked',
'🔓':'unlocked','🔏':'locked with pen','🔐':'locked with key','🔑':'key','🗝️':'old key','🔨':'hammer','🪓':'axe','⛏️':'pick','⚒️':'hammer and pick','🛠️':'hammer and wrench','🗡️':'dagger','⚔️':'crossed swords','🔫':'water pistol','🛡️':'shield','🔧':'wrench','🔩':'nut and bolt','⚙️':'gear','🗜️':'clamp','⚖️':'balance scale','🦯':'white cane','🔗':'link','⛓️':'chains','🧰':'toolbox','🧲':'magnet','🧪':'test tube','🧫':'petri dish','🧬':'dna','🔬':'microscope','🔭':'telescope','📡':'satellite antenna',
'💉':'syringe','🩸':'drop of blood','💊':'pill','🩹':'adhesive bandage','🩺':'stethoscope','🌡️':'thermometer','🚽':'toilet','🚰':'potable water','🚿':'shower','🛁':'bathtub','🛀':'person taking bath','🧴':'lotion bottle','🧷':'safety pin','🧹':'broom','🧺':'basket','🧻':'roll of paper','🧼':'soap','🧽':'sponge','🧯':'fire extinguisher','🛒':'shopping cart','🚬':'cigarette','⚰️':'coffin','⚱️':'funeral urn','🗿':'moai','🚂':'locomotive','🚃':'railway car','🚄':'high-speed train','🚅':'bullet train',
'🚆':'train','🚇':'metro','🚈':'light rail','🚉':'station','🚊':'tram','🚝':'monorail','🚞':'mountain railway','🚋':'tram car','🚌':'bus','🚍':'oncoming bus','🚎':'trolleybus','🚐':'minibus','🚑':'ambulance','🚒':'fire engine','🚓':'police car','🚔':'oncoming police car','🚕':'taxi','🚖':'oncoming taxi','🚗':'automobile','🚘':'oncoming automobile','🚙':'sport utility vehicle','🚚':'delivery truck','🚛':'articulated lorry','🚜':'tractor','🏎️':'racing car','🏍️':'motorcycle','🛵':'motor scooter','🦽':'manual wheelchair',
'🦼':'motorized wheelchair','🛺':'auto rickshaw','🚲':'bicycle','🛴':'kick scooter','🛼':'roller skate','🚏':'bus stop','🛣️':'motorway','🛤️':'railway track','🛢️':'oil drum','⛽':'fuel pump','🚨':'police car light','🚥':'horizontal traffic light','🚦':'vertical traffic light','🛑':'stop sign','🚧':'construction','⚓':'anchor','⛵':'sailboat','🛶':'canoe','🚤':'speedboat','🛳️':'passenger ship','⛴️':'ferry','🚢':'ship','✈️':'airplane','🛩️':'small airplane','🛫':'airplane departure','🛬':'airplane arrival',
'🪂':'parachute','💺':'seat','🚁':'helicopter','🚟':'suspension railway','🚠':'mountain cableway','🚡':'aerial tramway','🛰️':'satellite','🚀':'rocket','🛸':'flying saucer','🛎️':'bellhop bell','🧳':'luggage','⌛':'hourglass done','⏳':'hourglass not done','⌚':'watch','⏰':'alarm clock','⏱️':'stopwatch','⏲️':'timer clock','🕰️':'mantelpiece clock','🕛':'twelve o’clock','🕧':'twelve-thirty','🕐':'one o’clock','🕜':'one-thirty','🕑':'two o’clock','🕝':'two-thirty','🕒':'three o’clock','🕞':'three-thirty',
'🕓':'four o’clock','🕟':'four-thirty','🕔':'five o’clock','🕠':'five-thirty','🕕':'six o’clock','🕡':'six-thirty','🕖':'seven o’clock','🕢':'seven-thirty','🕗':'eight o’clock','🕣':'eight-thirty','🕘':'nine o’clock','🕤':'nine-thirty','🕙':'ten o’clock','🕥':'ten-thirty','🕚':'eleven o’clock','🕦':'eleven-thirty','🌠':'shooting star','🌌':'milky way','🌪️':'tornado','🌀':'cyclone','🌂':'closed umbrella','⛱️':'umbrella on ground',
'💯':'hundred points'
};

// Initialize everything after DOM is ready.
// Identity is resolved entirely by the server from the Home Assistant
// ingress login (see the /admin HA-mapping section) — there's no manual
// picker anymore. If Home Assistant couldn't resolve a name, the
// identityGate stays visible with instructions instead of the chat.
document.addEventListener('DOMContentLoaded', function() {
    restoreSidebarState();

    if (window.AUTO_CHAT_USER) {
        currentUser = window.AUTO_CHAT_USER;
        const gate = document.getElementById('identityGate');
        if (gate) gate.classList.add('hidden');

        const usernameEl = document.getElementById('currentUsername');
        const avatarEl = document.getElementById('currentAvatar');
        if (usernameEl) usernameEl.textContent = currentUser;
        if (avatarEl) avatarEl.innerHTML = avatarInnerHtml(window.AUTO_CHAT_USER_AVATAR, currentUser);

        initializeChat();
    }
    // else: leave identityGate visible (server already rendered the right
    // message — "ask an admin" vs "open via Home Assistant").
});

// All other functions below...

// Home Assistant ingress serves this app under a dynamic prefix like
// /api/hassio_ingress/<token>/ instead of the domain root. socket.io's
// default path option ("/socket.io/") ignores that prefix, so the
// WebSocket handshake gets routed wrong and never reaches the server.
// Deriving the path from the current URL fixes it for both ingress and
// plain (non-ingress) access.
function getIngressBasePath() {
    const path = window.location.pathname;
    return path.endsWith('/') ? path : path.substring(0, path.lastIndexOf('/') + 1);
}

// Every other place in this app that needed to guarantee a genuinely
// fresh response — the script tag's own version, every fetch() call —
// works by making the URL different every single time, never by
// trusting reload/cache-control behavior alone, because Home
// Assistant's ingress layer has a well-documented history throughout
// this app's own life of not reliably honoring Cache-Control: no-store.
// location.reload() was the one place that principle never got
// applied: it reloads the *exact same* URL, so if anything along the
// way ever cached that response even once, reload has nothing to force
// a fresh fetch with — confirmed as the actual cause of a real report
// (avatars needing a second manual refresh after changing one) that
// only showed up in Firefox, not Chrome, consistent with browsers
// genuinely differing in how aggressively they fall back to caching
// when a proxy's headers can't be fully trusted. Navigating to a URL
// with a fresh, unique query param instead guarantees a genuinely new
// request regardless of any of that.
function forceFreshReload() {
    const url = new URL(location.href);
    url.searchParams.set('_', Date.now());
    location.href = url.toString();
}

// The server returns root-relative API paths ("/api/messages") and file
// URLs ("/uploads/x.png"). A root-relative path resolves from the domain
// root in the browser, not from the current ingress-prefixed page, so
// under Home Assistant ingress every fetch() and every <img>/<video>/<a>
// pointed at one of these would silently 404. These two helpers rewrite
// them to be relative to the current (possibly ingress-prefixed) page.
function apiUrl(path) {
    return getIngressBasePath() + path.replace(/^\//, '');
}

function resolveUrl(url) {
    if (!url || !url.startsWith('/')) return url;
    return getIngressBasePath() + url.slice(1);
}

// --- Sidebar collapse/expand ---
// Each sidebar's collapsed state is remembered independently in
// localStorage, so reloading (or reopening the ingress panel) doesn't
// snap it back open.
const SIDEBAR_CONFIG = {
    channel: { id: 'channelSidebar', toggleId: 'channelSidebarToggle', storageKey: 'channelSidebarCollapsed', backdropId: 'channelSidebarBackdrop' },
    members: { id: 'membersSidebar', toggleId: 'membersSidebarToggle', storageKey: 'membersSidebarCollapsed' }
};

function setSidebarCollapsed(which, collapsed) {
    const cfg = SIDEBAR_CONFIG[which];
    if (!cfg) return;
    const el = document.getElementById(cfg.id);
    const btn = document.getElementById(cfg.toggleId);
    if (el) el.classList.toggle('collapsed', collapsed);
    if (btn) {
        btn.classList.toggle('active', collapsed);
        btn.setAttribute('aria-pressed', String(!collapsed));
    }
    // Only the channel sidebar becomes a mobile overlay drawer (see the
    // <768px media query) — the backdrop dims the chat behind it and
    // gives a tap-outside-to-close target, same as any other overlay in
    // this app. It's invisible/inert at wider widths regardless.
    if (cfg.backdropId) {
        const backdrop = document.getElementById(cfg.backdropId);
        if (backdrop) backdrop.classList.toggle('hidden', collapsed);
    }
    try { localStorage.setItem(cfg.storageKey, collapsed ? '1' : '0'); } catch (e) {}
}

function restoreSidebarState() {
    Object.keys(SIDEBAR_CONFIG).forEach(which => {
        const cfg = SIDEBAR_CONFIG[which];
        let collapsed;
        try { collapsed = localStorage.getItem(cfg.storageKey); } catch (e) { collapsed = null; }
        if (collapsed === null) {
            // No explicit preference saved yet — default to collapsed on
            // phone-width screens so a first-time mobile visitor lands
            // on the actual chat, not a sidebar drawer covering it.
            // Unchanged (expanded) on desktop, matching prior behavior.
            collapsed = window.innerWidth <= 768;
        } else {
            collapsed = collapsed === '1';
        }
        setSidebarCollapsed(which, collapsed);
    });
}

function toggleChannelSidebar() {
    const el = document.getElementById(SIDEBAR_CONFIG.channel.id);
    if (!el) return;
    setSidebarCollapsed('channel', !el.classList.contains('collapsed'));
}

function toggleMembersSidebar() {
    const el = document.getElementById(SIDEBAR_CONFIG.members.id);
    if (!el) return;
    setSidebarCollapsed('members', !el.classList.contains('collapsed'));
}

function initializeChat() {
    const basePath = getIngressBasePath();
    socket = io(window.location.origin, {
        path: basePath + 'socket.io/'
    });

    // The names people can @mention are read straight from the member
    // list already rendered on the page — the same list the person sees
    // in the sidebar, so a mention always matches someone actually
    // visible as a member, not some other identity string they'd have
    // no way to know. Populated once at load, matching how the member
    // list itself doesn't live-update either.
    window.mentionableNames = Array.from(document.querySelectorAll('.member[data-user]'))
        .map(el => el.dataset.user)
        .filter(Boolean);

    // The server always renders the first channel as "active" in the
    // initial HTML. If a different channel was restored from storage,
    // fix the sidebar/header to match it before anything loads — 
    // otherwise the highlighted channel and the messages shown for it
    // disagree with each other.
    document.querySelectorAll('.channel').forEach(ch => {
        ch.classList.toggle('active', ch.dataset.channel === currentChannel);
    });
    const initialChannelEl = document.getElementById('currentChannel');
    const initialWelcomeEl = document.getElementById('welcomeChannel');
    const initialInputEl = document.getElementById('messageInput');
    if (initialChannelEl) initialChannelEl.textContent = currentChannel;
    if (initialWelcomeEl) initialWelcomeEl.textContent = currentChannel;
    if (initialInputEl) initialInputEl.placeholder = `Message #${currentChannel}`;
    
    socket.on('connect', function() {
        console.log('Connected to server');
        socket.emit('join', {room: currentChannel});
    });
    
    socket.on('new_message', function(data) {
        const container = document.getElementById('messagesContainer');
        const wasNearBottom = isNearBottom(container);

        addMessage(data);

        // The client is only ever joined to the room for whichever
        // channel is currently open (see on_join() server-side), so
        // this only ever fires for the active channel — a mention in a
        // channel you're not currently viewing won't update its badge
        // live this way, only on the next switch to it or page reload.
        // Marking the active channel read again here stops a live
        // mention in the channel you're already looking at from
        // leaving a stale badge behind.
        if (data.channel === currentChannel) {
            markChannelRead(data.channel);
        }

        if (wasNearBottom) {
            scrollToBottom();
        } else {
            unseenMessageCount++;
            updateScrollToBottomBadge();
            updateScrollToBottomButton();
        }
        
        if (data.type === 'image' || data.type === 'gif' || (data.file && data.file.mime_type && data.file.mime_type.startsWith('image/'))) {
            addToSharedMedia(resolveUrl(data.file.url));
        }
    });
    
    socket.on('reaction_updated', function(data) {
        updateReaction(data.message_id, data.emoji, data.user, data.added);
    });

    socket.on('message_deleted', function(data) {
        removeMessageFromDom(data.message_id);
    });

    // If something goes wrong server-side while handling an event (a
    // failed send, a bad reaction, etc.), this is what used to fail
    // completely silently — now at least tell the person something broke.
    socket.on('server_error', function(data) {
        alert(data.message || 'Something went wrong. Check the add-on log for details.');
    });
    
    // Same reasoning as loadUpcomingEvents()'s fetch below: the server
    // already sends Cache-Control: no-store, but Home Assistant's
    // ingress iframe layer has a known history of not reliably honoring
    // that for in-page fetches. This is exactly the request that
    // decides what avatars show up in the message list on first load —
    // a stale cached response here looks exactly like "avatars don't
    // load until I refresh", which is precisely what was reported. The
    // timestamp query param alone is what actually does the work here —
    // it makes every request URL unique, so there's simply nothing for
    // any cache in that path to match against regardless of whether
    // it's honoring headers correctly. An earlier version of this fix
    // also added the fetch-level `cache: 'no-store'` option on top,
    // which turned out to make things worse rather than better —
    // avatars and the calendar stopped loading outright rather than
    // just being stale, on at least one real session. Removed again;
    // the URL uniqueness alone is the part actually doing anything.
    fetch(apiUrl(`/api/messages?channel=${currentChannel}&_=${Date.now()}`))
        .then(r => r.json())
        .then(messages => {
            messages.forEach(msg => addMessage(msg));
            // Establishes where "load older" should start from for this
            // first channel view — switchChannel() does the equivalent
            // for every channel switched to afterward.
            historyLoadState = {
                loading: false,
                hasMore: messages.length === HISTORY_PAGE_SIZE,
                oldestId: messages.length > 0 ? messages[0].id : null,
            };
            scrollToBottomRobust();
        })
        .catch(err => {
            // Previously silent — a failed fetch here (network blip,
            // server hiccup) looked exactly like an empty channel, with
            // no indication anything had gone wrong.
            console.error('Failed to load message history:', err);
            const container = document.getElementById('messagesContainer');
            if (container) {
                container.innerHTML = '<div class="welcome-message"><h1>Couldn\'t load messages</h1><p>Check your connection and try reloading.</p></div>';
            }
        });
    
    fetch(apiUrl(`/api/emojis?_=${Date.now()}`))
        .then(r => r.json())
        .then(emojis => {
            customEmojis = emojis;
        });

    loadUpcomingEvents();

    // The channel shown by default at page load never goes through
    // switchChannel() (which is what normally marks a channel read) —
    // it's just already there in the initial HTML. Marking it read here
    // covers that one case switchChannel() can't.
    markChannelRead(currentChannel);
    refreshChannelIndicators();
    // The only other trigger for this is switching channels — someone
    // who just stays put in one channel the whole time would otherwise
    // never see a badge for another channel light up until they
    // happened to navigate or reload. A light poll closes that gap
    // without needing a live per-user push channel just for this.
    setInterval(refreshChannelIndicators, 30000);
    
    const input = document.getElementById('messageInput');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                // The mention picker being open takes priority over
                // sending — Enter here means "pick the highlighted
                // match", the same as Tab does, not "send the message
                // with a half-typed @name still in it".
                if (mentionPickerState) {
                    e.preventDefault();
                    selectMentionMatch(mentionPickerState.matches[mentionPickerState.selectedIndex]);
                    return;
                }
                e.preventDefault();
                sendMessageClick();
            }
            // Enter alone still sends (preventDefault stops the newline
            // that a textarea would otherwise insert). Shift+Enter falls
            // through untouched — the browser's own default behavior for
            // Enter in a textarea is exactly "insert a newline", which is
            // what's wanted here, so there's nothing to add for that case.
        });
        // keydown, not keypress, for these — keypress doesn't reliably
        // fire for non-printable keys like the arrows or Escape across
        // browsers, only for character-producing ones.
        input.addEventListener('keydown', function(e) {
            if (!mentionPickerState) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                mentionPickerState.selectedIndex = (mentionPickerState.selectedIndex + 1) % mentionPickerState.matches.length;
                renderMentionPicker();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                mentionPickerState.selectedIndex = (mentionPickerState.selectedIndex - 1 + mentionPickerState.matches.length) % mentionPickerState.matches.length;
                renderMentionPicker();
            } else if (e.key === 'Tab') {
                e.preventDefault();
                selectMentionMatch(mentionPickerState.matches[mentionPickerState.selectedIndex]);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeMentionPicker();
            }
        });
        input.addEventListener('input', () => {
            autoResizeMessageInput(input);
            checkMentionTrigger(input);
        });
        // Clicking away from the input (without picking a match) should
        // close the picker rather than leave it stuck open pointing at
        // a cursor position that no longer means anything.
        input.addEventListener('blur', () => {
            // A timeout, not an immediate close: a click on a picker
            // item fires this blur event first, and closing right away
            // would remove the item from the DOM before its own click
            // handler gets a chance to run.
            setTimeout(closeMentionPicker, 150);
        });
    }
    
    document.querySelectorAll('.channel').forEach(ch => {
        ch.addEventListener('click', function() {
            switchChannel(this.dataset.channel);
        });
    });
    
    currentEmojiCategory = 'people';
    loadEmojiCategory('people');

    const emojiSearchInput = document.getElementById('emojiSearch');
    if (emojiSearchInput) {
        emojiSearchInput.addEventListener('input', () => searchEmojis(emojiSearchInput.value));
    }
}

// Grows the message box to fit multi-line content (up to the CSS
// max-height, past which it scrolls instead) and shrinks it back down
// again as lines are removed — resetting to 'auto' first is what makes
// the shrink direction work at all, since scrollHeight alone only ever
// reports how tall the content currently needs to be, not how much
// smaller the box could become.
function autoResizeMessageInput(input) {
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
}

// null when no reply is active, otherwise { id, sender, summary } —
// read by sendMessage() to attach reply_to_id to the outgoing socket
// payload, and cleared once that send actually goes out.
let replyContext = null;

function startReply(id) {
    const msgDiv = document.querySelector(`.message[data-id="${id}"]`);
    if (!msgDiv) return;
    replyContext = { id: Number(id), sender: msgDiv.dataset.sender, summary: msgDiv.dataset.replySummary };
    renderReplyPreview();
    const input = document.getElementById('messageInput');
    if (input) input.focus();
}

function cancelReply() {
    replyContext = null;
    renderReplyPreview();
}

function renderReplyPreview() {
    const bar = document.getElementById('replyPreviewBar');
    const senderEl = document.getElementById('replyPreviewSender');
    const textEl = document.getElementById('replyPreviewText');
    if (!bar || !senderEl || !textEl) return;
    if (!replyContext) {
        bar.classList.add('hidden');
        return;
    }
    senderEl.textContent = replyContext.sender;
    textEl.textContent = replyContext.summary;
    bar.classList.remove('hidden');
}

// Clicking a reply's quoted preview jumps to the original if it's
// currently loaded on-screen — delegated (rather than an inline
// onclick on every quote block) for the same reason .reaction pills
// already are: quote blocks come and go with every message rendered,
// a single document-level listener doesn't need re-attaching each time.
document.addEventListener('click', (e) => {
    const quote = e.target.closest('.message-reply-quote');
    if (!quote) return;
    const targetId = quote.dataset.jumpTo;
    const targetEl = document.querySelector(`.message[data-id="${targetId}"]`);
    // Not currently loaded (older than the most recent 100 in this
    // channel, or simply scrolled out and never rendered) — nothing
    // to scroll to, so this is a silent no-op rather than an error.
    if (!targetEl) return;
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    targetEl.classList.add('highlight-flash');
    setTimeout(() => targetEl.classList.remove('highlight-flash'), 2000);
});

// null when no @mention is actively being typed, otherwise
// { triggerStart, matches, selectedIndex } — triggerStart is the index
// of the '@' itself, so the whole "@partial" can be sliced out and
// replaced in one go once a match is picked.
let mentionPickerState = null;

function checkMentionTrigger(input) {
    const cursorPos = input.selectionStart;
    const textBeforeCursor = input.value.slice(0, cursorPos);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex === -1) {
        closeMentionPicker();
        return;
    }

    const partial = textBeforeCursor.slice(atIndex + 1);
    if (/\s/.test(partial)) {
        // Whitespace between the @ and the cursor means the cursor has
        // moved past whatever mention (if any) was being typed there.
        closeMentionPicker();
        return;
    }

    const charBeforeAt = atIndex > 0 ? textBeforeCursor[atIndex - 1] : '';
    if (charBeforeAt && !/\s/.test(charBeforeAt)) {
        // The @ isn't at a word boundary — "email@domain" mid-word,
        // not the start of a mention.
        closeMentionPicker();
        return;
    }

    if (!window.mentionableNames || window.mentionableNames.length === 0) {
        closeMentionPicker();
        return;
    }

    const partialLower = partial.toLowerCase();
    const matches = window.mentionableNames
        .filter(name => name.toLowerCase().startsWith(partialLower))
        .slice(0, 8);

    if (matches.length === 0) {
        closeMentionPicker();
        return;
    }

    // Reuse the existing state object across keystrokes rather than
    // replacing it outright, so a previously-navigated selectedIndex
    // doesn't just reset to 0 on every single character typed —
    // clamped afterward in case the new, narrower match list is
    // shorter than the old selected index.
    if (!mentionPickerState) mentionPickerState = { triggerStart: atIndex, matches: [], selectedIndex: 0 };
    mentionPickerState.triggerStart = atIndex;
    mentionPickerState.matches = matches;
    mentionPickerState.selectedIndex = Math.min(mentionPickerState.selectedIndex, matches.length - 1);
    renderMentionPicker();
}

function renderMentionPicker() {
    const picker = document.getElementById('mentionPicker');
    if (!picker || !mentionPickerState) return;

    picker.innerHTML = mentionPickerState.matches.map((name, i) =>
        `<div class="mention-picker-item${i === mentionPickerState.selectedIndex ? ' selected' : ''}" data-index="${i}">${escapeHtml(name)}</div>`
    ).join('');
    picker.classList.remove('hidden');

    picker.querySelectorAll('.mention-picker-item').forEach(el => {
        // mousedown rather than click, with preventDefault — this stops
        // the browser's default "clicking an element moves focus to
        // it" behavior, which means the textarea never actually loses
        // focus when picking a match with the mouse. That sidesteps
        // the close-on-blur handler entirely for the common case,
        // rather than racing against its setTimeout.
        el.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const idx = parseInt(el.dataset.index, 10);
            selectMentionMatch(mentionPickerState.matches[idx]);
        });
    });
}

function selectMentionMatch(name) {
    if (!mentionPickerState || !name) return;
    const input = document.getElementById('messageInput');
    if (!input) return;

    const cursorPos = input.selectionStart;
    const before = input.value.slice(0, mentionPickerState.triggerStart);
    const after = input.value.slice(cursorPos);
    // Only add a trailing space if there isn't one there already —
    // picking a mention mid-sentence (where a space already follows the
    // cursor, from whatever came after the partial mention) would
    // otherwise leave a double space behind.
    const insertion = `@${name}` + (after.startsWith(' ') ? '' : ' ');

    input.value = before + insertion + after;
    const newCursorPos = before.length + insertion.length;
    input.setSelectionRange(newCursorPos, newCursorPos);
    input.focus();

    closeMentionPicker();
    autoResizeMessageInput(input);
}

function closeMentionPicker() {
    if (!mentionPickerState) return;
    mentionPickerState = null;
    const picker = document.getElementById('mentionPicker');
    if (picker) {
        picker.classList.add('hidden');
        picker.innerHTML = '';
    }
}

function sendMessageClick() {
    const input = document.getElementById('messageInput');
    if (!input) return;
    
    const content = input.value.trim();
    
    if (content || selectedFile) {
        sendMessage(content);
        input.value = '';
        input.style.height = 'auto';
    }
}

function sendMessage(content) {
    const msgData = {
        sender: currentUser,
        content: content,
        channel: currentChannel,
        type: 'text'
    };
    
    if (selectedFile) {
        msgData.file = selectedFile;
        msgData.type = selectedFile.mime_type.startsWith('image/') ? 'image' : 
                       selectedFile.mime_type.startsWith('video/') ? 'video' : 'file';
        selectedFile = null;
        closeFileModal();
    }

    // Covers both the plain-text and the file/caption send paths, since
    // both funnel through here — a reply can carry an attachment too.
    if (replyContext) {
        msgData.reply_to_id = replyContext.id;
        cancelReply();
    }
    
    socket.emit('send_message', msgData);
}

// Per-channel state for "load older history on scroll up" — reset
// whenever the active channel changes (see switchChannel() and
// initializeChat()), since a fresh channel starts back at "we've only
// loaded the most recent page, there might be more above it".
// oldestId is always taken from whatever the most-recently-loaded
// page's own first message was — every page /api/messages returns
// comes back oldest-first (see get_messages() server-side), so that's
// reliably the oldest message currently in the DOM.
const HISTORY_PAGE_SIZE = 100; // must match get_messages()'s own default limit server-side
let historyLoadState = { loading: false, hasMore: true, oldestId: null };

function showHistoryLoadingIndicator(show) {
    const container = document.getElementById('messagesContainer');
    if (!container) return;
    let indicator = document.getElementById('historyLoadingIndicator');
    if (show) {
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'historyLoadingIndicator';
            indicator.className = 'history-loading-indicator';
            indicator.textContent = 'Loading older messages…';
            container.insertBefore(indicator, container.firstChild);
        }
    } else if (indicator) {
        indicator.remove();
    }
}

// Triggered by scrolling near the top of the message list (see the
// scroll listener further down) — fetches the next page of messages
// older than whatever's currently the oldest loaded, and prepends them
// without visibly jumping the scroll position.
function loadOlderMessages() {
    if (historyLoadState.loading || !historyLoadState.hasMore || historyLoadState.oldestId === null) return;
    historyLoadState.loading = true;
    showHistoryLoadingIndicator(true);

    fetch(apiUrl(`/api/messages?channel=${currentChannel}&before_id=${historyLoadState.oldestId}&_=${Date.now()}`))
        .then(r => r.json())
        .then(messages => {
            // Removed here, before any prepending — not in .finally(),
            // since .finally() runs after this .then() body, which would
            // leave the indicator sitting at the top *during* the prepend
            // loop below and end up wedged between the new messages and
            // the old ones instead of being cleanly gone first.
            showHistoryLoadingIndicator(false);
            historyLoadState.hasMore = messages.length === HISTORY_PAGE_SIZE;

            const container = document.getElementById('messagesContainer');
            if (messages.length > 0 && container) {
                const previousScrollHeight = container.scrollHeight;
                const previousScrollTop = container.scrollTop;
                historyLoadState.oldestId = messages[0].id;

                // The batch itself is oldest-first, but has to be walked
                // backwards here — prepending one at a time, each new
                // message goes at the very top, so inserting the batch's
                // newest member first and its oldest member last is the
                // only order that leaves the finished batch itself
                // correctly oldest-to-newest once every insert is done.
                for (let i = messages.length - 1; i >= 0; i--) {
                    addMessage(messages[i], 'prepend');
                }

                // Prepending content above the visible area pushes
                // everything else down by the same amount — scrollTop
                // would stay numerically the same but now point at a
                // completely different spot in the now-taller content,
                // which from the person's perspective looks like the
                // view suddenly jumping. Growing scrollTop by exactly how
                // much scrollHeight grew keeps them looking at the same
                // message they were already looking at.
                const newScrollHeight = container.scrollHeight;
                container.scrollTop = previousScrollTop + (newScrollHeight - previousScrollHeight);
            }
        })
        .catch(err => {
            console.error('Failed to load older messages:', err);
            showHistoryLoadingIndicator(false);
        })
        .finally(() => {
            historyLoadState.loading = false;
        });
}

function addMessage(data, insertMode = 'append') {
    const container = document.getElementById('messagesContainer');
    if (!container) return;

    // Messages loaded from history (/api/messages) come back with the
    // field named message_type — the actual database column name.
    // Messages delivered live over the socket use type instead, set
    // explicitly in each socket emit. Normalized once here rather than
    // at each call site, so nothing added later falls into the same
    // gap this already caused: a calendar event rendered as raw JSON
    // text instead of its card, specifically because history-loaded
    // messages never had a `type` field at all to match against.
    const msgType = data.type || data.message_type || 'text';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.dataset.id = data.id;
    // Stashed here (rather than recomputed later) so startReply() can
    // read them straight off the DOM when this message gets replied to
    // — avoids needing a second, separate lookup path against the
    // original data for every message ever rendered, most of which
    // will never actually be replied to.
    messageDiv.dataset.sender = data.sender || '';
    messageDiv.dataset.replySummary = summarizeMessageForReply(data, msgType);
    
    const time = new Date(data.timestamp).toLocaleTimeString([], {
        hour: '2-digit', 
        minute: '2-digit'
    });
    
    let contentHtml = msgType === 'calendar_event'
        ? buildCalendarEventHtml(data.content)
        : `<div class="message-text">${renderMessageText(data.content)}</div>`;

    // A reply's quote sits above its own content — built from the
    // snapshot save_message() took server-side at send time (see
    // reply_to_sender/reply_to_summary), not a live lookup against the
    // original message, so it keeps showing correctly even if that
    // original was since deleted or isn't currently loaded.
    // data-jump-to is handled by a single delegated listener further
    // down, which just no-ops if the original isn't on-screen to jump to.
    const replyQuoteHtml = data.reply_to_id ? `
        <div class="message-reply-quote" data-jump-to="${data.reply_to_id}">
            <span class="reply-quote-sender">${escapeHtml(data.reply_to_sender || 'Someone')}</span>
            <span class="reply-quote-text">${escapeHtml(data.reply_to_summary || '')}</span>
        </div>
    ` : '';
    
    if (data.file || data.file_url) {
        const rawFileName = data.file?.filename || data.file_name || '';
        const fileUrl = safeUrl(resolveUrl(data.file?.url || data.file_url));
        const fileName = escapeHtml(rawFileName);
        const mimeType = escapeHtml(data.file?.mime_type || data.mime_type || '');
        
        if (looksLikeImageFile(mimeType, rawFileName)) {
            contentHtml += `
                <div class="message-image" onclick="openImageViewer('${fileUrl}')">
                    <img src="${fileUrl}" alt="${fileName}" loading="lazy">
                </div>
            `;
        } else if (mimeType && mimeType.startsWith('video/')) {
            contentHtml += `
                <div class="message-video">
                    <video controls preload="metadata">
                        <source src="${fileUrl}" type="${mimeType}">
                    </video>
                </div>
            `;
        } else {
            const fileSize = formatFileSize(data.file?.size || data.file_size || 0);
            const fileIcon = getFileIcon(mimeType);
            contentHtml += `
                <div class="message-file">
                    <a href="${fileUrl}" target="_blank" class="file-attachment">
                        <div class="file-icon">${fileIcon}</div>
                        <div class="file-info">
                            <div class="file-name">${fileName}</div>
                            <div class="file-size">${fileSize}</div>
                        </div>
                    </a>
                </div>
            `;
        }
    }
    
    const reactionsHtml = buildReactionsHtml(data.id, data.reactions || {});
    messageReactions[data.id] = data.reactions || {};

    // Own messages are deletable by their sender; any message is
    // deletable by an admin (window.IS_ADMIN — an authenticated /admin
    // session in *this* browser) or the designated owner (window.IS_OWNER
    // — tied to this person's Home Assistant identity, no password
    // needed).
    const canDelete = !!data.sender_id &&
        (data.sender_id === window.AUTO_CHAT_USER_ID || window.IS_ADMIN || window.IS_OWNER);
    const deleteBtnHtml = canDelete
        ? `<button class="action-btn action-btn-danger" onclick="deleteMessage(${data.id})" title="Delete message">🗑️</button>`
        : '';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarInnerHtml(data.avatar_url, data.sender)}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${escapeHtml(data.sender)}</span>
                <span class="message-timestamp">${time}</span>
            </div>
            ${replyQuoteHtml}
            ${contentHtml}
            ${reactionsHtml}
        </div>
        <div class="message-actions">
            <button class="action-btn" onclick="startReply(${data.id})" title="Reply">↩️</button>
            <button class="action-btn" onclick="openReactionPicker(${data.id}, this)" title="Add reaction">😊</button>
            ${deleteBtnHtml}
        </div>
    `;
    
    // 'prepend' is used when loading older history (see
    // loadOlderMessages()) — inserting one at a time at the very top of
    // an already-scrolled container is why that function walks its
    // batch backwards rather than forwards; every other call site
    // (live messages, initial channel load, search-result jumps) keeps
    // the default append.
    if (insertMode === 'prepend') {
        container.insertBefore(messageDiv, container.firstChild);
    } else {
        container.appendChild(messageDiv);
    }
}

// Reaction pills for every message currently rendered, keyed by message
// id: { emoji: [usernames who reacted with it] }. Kept in memory so a
// live 'reaction_updated' event can patch just the one message's pills
// back into the DOM without needing to reload the whole channel.
const messageReactions = {};

function buildReactionsHtml(messageId, reactions) {
    if (!reactions || Object.keys(reactions).length === 0) return '';
    let html = '<div class="message-reactions">';
    for (const [emoji, users] of Object.entries(reactions)) {
        if (!users || users.length === 0) continue;
        const isActive = users.includes(currentUser);
        // The emoji goes in a data-attribute (browser-decoded on read via
        // .dataset) rather than interpolated into an onclick="..." string
        // — a custom emoji name or username with a quote in it would
        // otherwise be able to break out of the attribute.
        html += `
            <div class="reaction ${isActive ? 'active' : ''}" data-message-id="${messageId}" data-emoji="${escapeHtml(emoji)}">
                ${escapeHtml(emoji)} <span class="reaction-count">${users.length}</span>
            </div>
        `;
    }
    html += '</div>';
    return html;
}

function renderMessageReactions(messageId) {
    const messageDiv = document.querySelector(`.message[data-id="${messageId}"]`);
    if (!messageDiv) return;
    const content = messageDiv.querySelector('.message-content');
    if (!content) return;

    const existing = content.querySelector('.message-reactions');
    const html = buildReactionsHtml(messageId, messageReactions[messageId]);

    if (!html) {
        if (existing) existing.remove();
        return;
    }
    if (existing) {
        existing.outerHTML = html;
    } else {
        content.insertAdjacentHTML('beforeend', html);
    }
}

// Clicking any reaction pill toggles it — handled here via delegation
// (rather than a per-pill onclick) since pills are re-created often as
// reactions come and go.
document.addEventListener('click', (e) => {
    const pill = e.target.closest('.reaction');
    if (!pill) return;
    const messageId = pill.dataset.messageId;
    const emoji = pill.dataset.emoji;
    if (messageId && emoji) toggleReaction(Number(messageId), emoji);
});

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) container.scrollTop = container.scrollHeight;
}

// Images finish loading asynchronously, after they've already been
// inserted into the DOM — each one that loads grows the page a bit more.
// A single scrollToBottom() called right after rendering measures the
// page before that growth happens, so on a channel with attachments you
// can land noticeably above the actual most recent message. This re-runs
// the scroll whenever a newly-added image finishes loading (or fails to).
function scrollToBottomRobust() {
    scrollToBottom();
    const container = document.getElementById('messagesContainer');
    if (!container) return;
    container.querySelectorAll('img').forEach(img => {
        if (!img.complete) {
            img.addEventListener('load', scrollToBottom, { once: true });
            img.addEventListener('error', scrollToBottom, { once: true });
        }
    });
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    // Escaping quotes too (not just <, >, &) matters because this value
    // often gets dropped into an HTML *attribute* (onclick="...", alt="..."),
    // not just text content — a bare quote character there breaks out of
    // the attribute and enables injecting arbitrary attributes/handlers.
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Turns http(s) URLs in plain message text into clickable links. Escapes
// everything itself (both the surrounding text and the URLs) — callers
// should NOT also run escapeHtml() on text passed through here, or
// entities would get double-escaped.
// Swaps @Name for an opaque placeholder token BEFORE linkifyText runs,
// and hands back the real names separately rather than embedding them
// in the placeholder text itself — anything embedded would go through
// linkifyText's own HTML-escaping pass along with the surrounding text,
// and escaping a name a second time on the way back out (a name with an
// apostrophe, say) would show literal &#39; instead of an apostrophe.
// Keeping the names in an array and re-inserting by index sidesteps
// that entirely. Longest names first, so "@John Smith" matches whole
// rather than a shorter "@John" grabbing part of it.
function highlightMentions(text) {
    if (!text || !window.mentionableNames || window.mentionableNames.length === 0) {
        return { text: text || '', mentions: [] };
    }
    const sorted = [...window.mentionableNames].sort((a, b) => b.length - a.length);
    const pattern = sorted.map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
    // (?!\w) rather than \b at the end — \b only fires on a transition
    // between a word and non-word character, which breaks for a name
    // that itself ends in punctuation ("A.J.", "Jon Jr."): the period
    // and the space after it are both non-word characters, so \b can
    // never find a valid transition there and the match silently fails.
    // (?!\w) just asserts "not immediately followed by a word
    // character" — true end-of-string included — which is what's
    // actually wanted and correctly covers ordinary names too.
    const mentionRegex = new RegExp(`@(${pattern})(?!\\w)`, 'g');
    const mentions = [];
    const replaced = text.replace(mentionRegex, (match, name) => {
        const idx = mentions.length;
        mentions.push(name);
        return `\x00MENTION${idx}\x00`;
    });
    return { text: replaced, mentions };
}

function restoreMentionPlaceholders(html, mentions) {
    if (!mentions || mentions.length === 0) return html;
    return html.replace(/\x00MENTION(\d+)\x00/g, (match, idxStr) => {
        const name = mentions[Number(idxStr)];
        return name !== undefined ? `<span class="mention">@${escapeHtml(name)}</span>` : match;
    });
}

// The one place both of the above should actually be used — wraps
// linkifyText so every call site (the message feed, search results)
// gets mention highlighting applied consistently, in the right order,
// without each one having to know about the placeholder mechanism.
function renderMessageText(text) {
    const { text: preprocessed, mentions } = highlightMentions(text || '');
    return restoreMentionPlaceholders(linkifyText(preprocessed), mentions);
}

function linkifyText(text) {
    if (!text) return '';
    const urlPattern = /https?:\/\/[^\s<>"']+/g;
    let result = '';
    let lastIndex = 0;
    let match;

    while ((match = urlPattern.exec(text)) !== null) {
        let url = match[0];
        let end = match.index + url.length;

        // Trailing punctuation almost always belongs to the sentence,
        // not the link — "check this out: https://example.com." should
        // not swallow the period. Strips one character at a time so
        // something like "(see https://example.com)." unwraps correctly
        // in either order. A closing paren/bracket is only stripped if
        // it doesn't have a matching opener earlier in the URL, since
        // some real URLs (e.g. Wikipedia article titles) legitimately
        // end in one.
        let trimmed = true;
        while (trimmed && url.length > 0) {
            trimmed = false;
            if (/[.,!?:;]$/.test(url)) {
                url = url.slice(0, -1);
                end -= 1;
                trimmed = true;
            } else if (url.endsWith(')') && (url.match(/\(/g) || []).length < (url.match(/\)/g) || []).length) {
                url = url.slice(0, -1);
                end -= 1;
                trimmed = true;
            } else if (url.endsWith(']') && (url.match(/\[/g) || []).length < (url.match(/\]/g) || []).length) {
                url = url.slice(0, -1);
                end -= 1;
                trimmed = true;
            }
        }
        if (!url) continue;

        result += escapeHtml(text.slice(lastIndex, match.index));
        const safeHref = escapeHtml(url); // url is guaranteed http(s):// by the regex, and can't contain a quote character (excluded from the match), so this is just attribute-encoding, not a scheme check
        // stopPropagation matters here: linkifyText() output sometimes
        // ends up inside an element that itself has its own onclick (a
        // search result row navigates to the message it's from) — without
        // this, clicking the link would both open it AND trigger that.
        result += `<a href="${safeHref}" target="_blank" rel="noopener noreferrer nofollow" onclick="event.stopPropagation()">${escapeHtml(url)}</a>`;
        lastIndex = end;
        urlPattern.lastIndex = end; // resume scanning right after whatever we actually linked, since trimming may have moved it earlier than the raw regex match
    }
    result += escapeHtml(text.slice(lastIndex));
    return result;
}

// Shared by every place an avatar circle gets rendered client-side (chat
// messages; the "me" panel and settings preview refresh after an
// upload) — a real photo if the person has set one, else the same
// first-letter-of-name fallback this app has always shown.
function avatarInnerHtml(avatarUrl, name) {
    if (avatarUrl) {
        return `<img src="${safeUrl(resolveUrl(avatarUrl))}" alt="" class="avatar-img">`;
    }
    return escapeHtml((name || '?')[0]);
}

function safeUrl(url) {
    // Only allow relative paths or http(s) URLs into src/href attributes.
    // Without this, a spoofed file/emoji URL (these can still be
    // client-supplied in the socket payload) could use a "javascript:" or
    // "data:" scheme to run script when clicked/rendered.
    if (!url) return '#';
    const s = String(url);
    if (s.startsWith('/') || s.startsWith('./') || s.startsWith('http://') || s.startsWith('https://')) {
        return escapeHtml(s);
    }
    return '#';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Browsers don't always supply a Content-Type for an upload — some OS/
// browser/file-type combinations leave it blank, which would otherwise
// silently downgrade a real image to a generic file-attachment block
// (icon + filename, no preview) even though it's perfectly viewable.
// When there's no mime type to go on, fall back to the file extension
// rather than assuming "not an image".
function looksLikeImageFile(mimeType, filename) {
    if (mimeType) return mimeType.startsWith('image/');
    const ext = (filename || '').split('.').pop().toLowerCase();
    return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(ext);
}

function getFileIcon(mimeType) {
    if (mimeType?.startsWith('image/')) return '🖼️';
    if (mimeType?.startsWith('video/')) return '🎬';
    if (mimeType?.startsWith('audio/')) return '🎵';
    if (mimeType?.includes('pdf')) return '📄';
    return '📎';
}

function uploadFile(file) {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch(apiUrl('/api/upload'), {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            selectedFile = data;
            showFilePreview(data, file);
        } else {
            alert('Upload failed: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Upload error:', err);
        alert('Upload failed');
    });
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    uploadFile(file);
    event.target.value = '';
}

// Pasting a screenshot (or any copied image) anywhere on the page — not
// just while the message box itself is focused — uploads it the same
// way picking a file with 📎 does. This has to be document-level rather
// than scoped to #messageInput: the first pasted image opens the
// caption/preview modal, which moves focus into the caption field, so a
// listener only on the message input would stop firing after exactly
// one paste — a real bug that shipped in the first version of this.
function handlePasteImage(event) {
    const items = event.clipboardData && event.clipboardData.items;
    if (!items) return;

    for (const item of items) {
        if (item.kind === 'file' && item.type && item.type.startsWith('image/')) {
            const file = item.getAsFile();
            if (!file) continue;
            // A pasted image typically has no real filename — give it
            // one so it doesn't show up downstream as a bare "image.png"
            // with no useful info.
            const ext = (item.type.split('/')[1] || 'png').split('+')[0];
            const named = new File([file], `pasted-screenshot-${Date.now()}.${ext}`, { type: item.type });
            event.preventDefault(); // don't also let the browser try to paste raw image bytes as text
            uploadFile(named);
            break; // only the first image if somehow more than one was pasted at once
        }
    }
}
document.addEventListener('paste', handlePasteImage);

// Avatar crop drag — mouse/touch listeners live on the document (not
// just the viewport element) for move/end specifically, since a drag
// that started inside the circular viewport should keep tracking even
// if the pointer moves outside it mid-drag, rather than dropping the
// gesture the instant the cursor crosses the viewport's edge.
document.addEventListener('DOMContentLoaded', () => {
    const viewport = document.getElementById('avatarCropViewport');
    if (!viewport) return;
    viewport.addEventListener('mousedown', onAvatarCropDragStart);
    viewport.addEventListener('touchstart', onAvatarCropDragStart, { passive: false });
    document.addEventListener('mousemove', onAvatarCropDragMove);
    document.addEventListener('touchmove', onAvatarCropDragMove, { passive: false });
    document.addEventListener('mouseup', onAvatarCropDragEnd);
    document.addEventListener('touchend', onAvatarCropDragEnd);

    const zoomSlider = document.getElementById('avatarCropZoom');
    if (zoomSlider) zoomSlider.addEventListener('input', onAvatarCropZoomChange);
});


function showFilePreview(data, file) {
    const modal = document.getElementById('fileModal');
    const content = document.getElementById('filePreviewContent');
    if (!modal || !content) return;
    
    if (data.mime_type.startsWith('image/')) {
        content.innerHTML = `<img src="${safeUrl(resolveUrl(data.url))}" alt="${escapeHtml(data.filename)}">`;
    } else if (data.mime_type.startsWith('video/')) {
        content.innerHTML = `<video controls><source src="${safeUrl(resolveUrl(data.url))}" type="${escapeHtml(data.mime_type)}"></video>`;
    } else {
        content.innerHTML = `
            <div class="file-attachment" style="padding: 32px;">
                <div class="file-icon" style="width: 64px; height: 64px; font-size: 32px;">${getFileIcon(data.mime_type)}</div>
                <div class="file-info">
                    <div class="file-name">${escapeHtml(data.filename)}</div>
                    <div class="file-size">${formatFileSize(data.size)}</div>
                </div>
            </div>
        `;
    }
    
    modal.classList.remove('hidden');
}

function closeFileModal() {
    const modal = document.getElementById('fileModal');
    if (modal) modal.classList.add('hidden');
    selectedFile = null;
}

function sendFile() {
    const captionInput = document.getElementById('fileCaption');
    const caption = captionInput ? captionInput.value : '';
    sendMessage(caption);
}

function toggleEmojiPicker() {
    const picker = document.getElementById('emojiPicker');
    if (!picker) return;
    const gifPicker = document.getElementById('gifPicker');
    if (gifPicker) gifPicker.classList.add('hidden');

    // If it's already open for composing (no reaction context), this
    // click closes it. Otherwise (closed, or open for a reaction) this
    // click (re)opens it anchored to the composer as normal.
    const isOpenForCompose = !picker.classList.contains('hidden') && !emojiPickerContext;
    if (isOpenForCompose) {
        hideEmojiPicker();
        return;
    }
    resetEmojiPickerPosition();
    emojiPickerContext = null;
    picker.classList.remove('hidden');
    // Clears any leftover search text/results from a previous open (e.g.
    // if it was last used as a reaction picker) so it comes back showing
    // whichever tab was last selected.
    clearEmojiSearchInput();
    switchEmojiTabProgrammatic(currentEmojiCategory);
}

function resetEmojiPickerPosition() {
    const picker = document.getElementById('emojiPicker');
    if (!picker) return;
    picker.style.position = '';
    picker.style.top = '';
    picker.style.left = '';
    picker.style.right = '';
    picker.style.bottom = '';
}

function hideEmojiPicker() {
    const picker = document.getElementById('emojiPicker');
    if (!picker) return;
    picker.classList.add('hidden');
    resetEmojiPickerPosition();
    emojiPickerContext = null;
}

function switchEmojiTab(category) {
    document.querySelectorAll('.emoji-tab').forEach(t => t.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
    currentEmojiCategory = category;
    clearEmojiSearchInput();
    loadEmojiCategory(category);
}

function loadEmojiCategory(category) {
    const grid = document.getElementById('emojiGrid');
    if (!grid) return;
    grid.innerHTML = '';
    
    let emojis = [];
    if (category === 'recent') {
        emojis = recentEmojis;
        if (emojis.length === 0) {
            grid.innerHTML = '<div class="emoji-empty">No recent emoji yet</div>';
            return;
        }
    } else if (category === 'custom') {
        if (Object.keys(customEmojis).length === 0) {
            grid.innerHTML = '<div class="emoji-empty">No custom emojis yet</div>';
            return;
        }
        Object.entries(customEmojis).forEach(([name, url]) => {
            const item = document.createElement('div');
            item.className = 'emoji-item';
            item.title = name;
            item.innerHTML = `<img src="${safeUrl(resolveUrl(url))}" alt="${escapeHtml(name)}" style="width: 28px; height: 28px;">`;
            item.onclick = () => insertEmoji(name);
            grid.appendChild(item);
        });
        return;
    } else {
        emojis = emojiCategories[category] || [];
    }
    
    emojis.forEach(emoji => {
        const item = document.createElement('div');
        item.className = 'emoji-item';
        item.textContent = emoji;
        item.title = emojiNames[emoji] || '';
        item.onclick = () => insertEmoji(emoji);
        grid.appendChild(item);
    });
}

function clearEmojiSearchInput() {
    const searchInput = document.getElementById('emojiSearch');
    if (searchInput) searchInput.value = '';
}

// Live filter as the person types. Unicode emoji are matched against the
// generated `emojiNames` labels (the characters themselves aren't
// searchable text); custom emojis are matched against their :name:.
// Matches are pooled across every category at once rather than just
// whichever tab happens to be selected — that's what makes typing
// "cat" find 🐱 even while the Food tab is showing.
function searchEmojis(query) {
    const grid = document.getElementById('emojiGrid');
    if (!grid) return;
    const q = query.trim().toLowerCase();

    if (!q) {
        document.querySelectorAll('.emoji-tab').forEach(t => t.classList.remove('active'));
        const activeTab = document.querySelector(`.emoji-tab[onclick="switchEmojiTab('${currentEmojiCategory}')"]`);
        if (activeTab) activeTab.classList.add('active');
        loadEmojiCategory(currentEmojiCategory);
        return;
    }

    document.querySelectorAll('.emoji-tab').forEach(t => t.classList.remove('active'));
    grid.innerHTML = '';

    const seen = new Set();
    const matches = [];
    Object.values(emojiCategories).forEach(list => {
        list.forEach(emoji => {
            if (seen.has(emoji)) return;
            const name = emojiNames[emoji];
            if (name && name.includes(q)) {
                seen.add(emoji);
                matches.push({ type: 'unicode', emoji, name });
            }
        });
    });
    Object.entries(customEmojis).forEach(([name, url]) => {
        if (name.replace(/:/g, '').toLowerCase().includes(q)) {
            matches.push({ type: 'custom', name, url });
        }
    });

    if (matches.length === 0) {
        grid.innerHTML = '<div class="emoji-empty">No emoji found</div>';
        return;
    }

    // Cap results so an extremely broad query (e.g. a single common
    // letter) doesn't render hundreds of grid items at once.
    matches.slice(0, 200).forEach(match => {
        const item = document.createElement('div');
        item.className = 'emoji-item';
        if (match.type === 'unicode') {
            item.textContent = match.emoji;
            item.title = match.name;
            item.onclick = () => insertEmoji(match.emoji);
        } else {
            item.title = match.name;
            item.innerHTML = `<img src="${safeUrl(resolveUrl(match.url))}" alt="${escapeHtml(match.name)}" style="width: 28px; height: 28px;">`;
            item.onclick = () => insertEmoji(match.name);
        }
        grid.appendChild(item);
    });
}

function insertEmoji(emoji) {
    if (!recentEmojis.includes(emoji)) {
        recentEmojis.unshift(emoji);
        if (recentEmojis.length > 32) recentEmojis.pop();
        try { localStorage.setItem('recentEmojis', JSON.stringify(recentEmojis)); } catch (e) {}
    }

    if (emojiPickerContext && emojiPickerContext.messageId) {
        toggleReaction(emojiPickerContext.messageId, emoji);
        hideEmojiPicker();
        return;
    }

    const input = document.getElementById('messageInput');
    if (input) input.value += emoji;
}

function switchChannel(slug, onLoaded) {
    document.querySelectorAll('.channel').forEach(c => {
        c.classList.toggle('active', c.dataset.channel === slug);
    });
    currentChannel = slug;
    try { localStorage.setItem('lastChannel', currentChannel); } catch (e) {}
    // A reply is tied to a message in the channel you were just in —
    // switching wipes that channel's messages from the DOM entirely, so
    // the original wouldn't even be visible anymore. Left active, the
    // preview bar would keep showing a stale "Replying to..." for a
    // message the person can no longer even see.
    cancelReply();
    markChannelRead(slug);
    // Marking the newly-active channel read only ever handles that one
    // channel — this is what actually picks up a mention (or general
    // unread activity) that happened in some *other* channel while you
    // were elsewhere, which nothing else was doing. Without it,
    // indicators only ever reflected whatever was true at the last full
    // page load, no matter how much navigating around happened in
    // between.
    refreshChannelIndicators();

    // On phone-width screens the channel sidebar is a slide-over drawer
    // (see the <768px media query) — picking a channel from it should
    // close it afterward the way any mobile nav drawer would, rather
    // than leaving it covering the very channel you just switched to.
    if (window.innerWidth <= 768) {
        setSidebarCollapsed('channel', true);
    }

    // A different channel is a fresh view, always landing at the bottom
    // (see below) — any unseen count from the channel just left doesn't
    // carry over.
    unseenMessageCount = 0;
    updateScrollToBottomBadge();
    const scrollBtn = document.getElementById('scrollToBottomBtn');
    if (scrollBtn) scrollBtn.classList.add('hidden');

    const channelEl = document.getElementById('currentChannel');
    const welcomeEl = document.getElementById('welcomeChannel');
    const inputEl = document.getElementById('messageInput');

    if (channelEl) channelEl.textContent = currentChannel;
    if (welcomeEl) welcomeEl.textContent = currentChannel;
    if (inputEl) inputEl.placeholder = `Message #${currentChannel}`;

    const container = document.getElementById('messagesContainer');
    if (container) {
        container.innerHTML = `
            <div class="welcome-message">
                <h1>Welcome to #${currentChannel}!</h1>
                <p>Stay connected with your family 👨‍👩‍👧‍👦</p>
            </div>
        `;
    }
    // Cleared immediately rather than waiting on the fetch below to
    // resolve — otherwise a scroll during that brief window could
    // trigger loadOlderMessages() using the *previous* channel's
    // oldestId against a container that no longer holds any of its
    // messages.
    historyLoadState = { loading: false, hasMore: false, oldestId: null };

    if (socket) socket.emit('join', {room: currentChannel});

    fetch(apiUrl(`/api/messages?channel=${currentChannel}&_=${Date.now()}`))
        .then(r => r.json())
        .then(messages => {
            messages.forEach(msg => addMessage(msg));
            // Same reasoning as initializeChat()'s equivalent — this
            // channel's own "load older" cursor, freshly established
            // for whatever just got loaded here.
            historyLoadState = {
                loading: false,
                hasMore: messages.length === HISTORY_PAGE_SIZE,
                oldestId: messages.length > 0 ? messages[0].id : null,
            };
            if (onLoaded) {
                // Jumping to a specific message (e.g. from search) — scroll
                // there first, then let the caller's own scroll-into-view
                // take over. Using the robust/image-aware scroll here could
                // yank the view back down to the bottom later if an image
                // above the target message finishes loading after we've
                // already landed on it.
                scrollToBottom();
                onLoaded();
            } else {
                scrollToBottomRobust();
            }
        })
        .catch(err => {
            console.error('Failed to load message history:', err);
            const container = document.getElementById('messagesContainer');
            if (container) {
                container.innerHTML = '<div class="welcome-message"><h1>Couldn\'t load messages</h1><p>Check your connection and try reloading.</p></div>';
            }
        });
}

function toggleSearch() {
    const modal = document.getElementById('searchModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    const input = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (input) { input.value = ''; input.focus(); }
    if (results) results.innerHTML = '<p class="hint">Type at least 2 characters and press Enter, or click Search.</p>';
}

function closeSearch() {
    const modal = document.getElementById('searchModal');
    if (modal) modal.classList.add('hidden');
}

function runSearch() {
    const input = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (!input || !results) return;
    const q = input.value.trim();
    if (q.length < 2) {
        results.innerHTML = '<p class="hint">Type at least 2 characters to search.</p>';
        return;
    }
    results.innerHTML = '<p class="hint">Searching…</p>';
    fetch(apiUrl(`/api/search?q=${encodeURIComponent(q)}`))
        .then(r => r.json())
        .then(matches => {
            if (!matches.length) {
                results.innerHTML = '<p class="hint">No messages found.</p>';
                return;
            }
            results.innerHTML = '';
            matches.forEach(m => {
                const item = document.createElement('div');
                item.className = 'search-result';
                const time = new Date(m.timestamp).toLocaleString();
                item.innerHTML = `
                    <div class="search-result-meta">${escapeHtml(m.channel_icon)} ${escapeHtml(m.channel_name)} · <strong>${escapeHtml(m.sender)}</strong> · ${escapeHtml(time)}</div>
                    <div class="search-result-content">${renderMessageText(m.content)}</div>
                `;
                item.onclick = () => jumpToSearchResult(m);
                results.appendChild(item);
            });
        })
        .catch(() => {
            results.innerHTML = '<p class="hint">Search failed — check the add-on log.</p>';
        });
}

function jumpToSearchResult(m) {
    closeSearch();
    switchChannel(m.channel, () => {
        const el = document.querySelector(`[data-id="${m.id}"]`);
        if (el) {
            el.scrollIntoView({behavior: 'smooth', block: 'center'});
            el.classList.add('highlight-flash');
            setTimeout(() => el.classList.remove('highlight-flash'), 2000);
        }
        // Older messages beyond the most recent 100 in a channel aren't
        // loaded yet — there's no "load more history" yet, so very old
        // results land you on the channel but won't auto-scroll to it.
    });
}

function openFileBrowser() {
    const modal = document.getElementById('filesModal');
    const list = document.getElementById('filesList');
    if (!modal || !list) return;
    modal.classList.remove('hidden');
    list.innerHTML = '<p class="hint">Loading…</p>';
    fetch(apiUrl(`/api/files?channel=${currentChannel}`))
        .then(r => r.json())
        .then(files => {
            if (!files.length) {
                list.innerHTML = '<p class="hint">No files shared in this channel yet.</p>';
                return;
            }
            list.innerHTML = '';
            files.forEach(f => {
                const item = document.createElement('a');
                item.className = 'file-browser-item';
                item.href = safeUrl(resolveUrl(f.url));
                item.target = '_blank';
                item.rel = 'noopener';
                const time = new Date(f.timestamp).toLocaleString();
                item.innerHTML = `
                    <div class="file-icon">${getFileIcon(f.mime_type)}</div>
                    <div class="file-info">
                        <div class="file-name">${escapeHtml(f.filename || 'file')}</div>
                        <div class="file-size">${escapeHtml(f.sender)} · ${formatFileSize(f.size || 0)} · ${escapeHtml(time)}</div>
                    </div>
                `;
                list.appendChild(item);
            });
        })
        .catch(() => {
            list.innerHTML = '<p class="hint">Failed to load files — check the add-on log.</p>';
        });
}

function closeFileBrowser() {
    const modal = document.getElementById('filesModal');
    if (modal) modal.classList.add('hidden');
}

// --- Calendar ---
// Fetches its dropdowns fresh every time the modal opens rather than
// caching them client-side — calendars and channels can both change
// between opens, and this form is opened rarely enough (compared to,
// say, the emoji picker) that the extra round-trip isn't worth
// optimizing away.
function openCalendarModal() {
    const modal = document.getElementById('calendarModal');
    if (!modal) return;
    modal.classList.remove('hidden');

    // Reset to a blank, timed (non-all-day) event every time it opens,
    // rather than leaving whatever was last typed — this form is for
    // adding one specific thing and closing, not something you'd want
    // to reopen mid-edit.
    document.getElementById('calEventTitle').value = '';
    document.getElementById('calEventLocation').value = '';
    document.getElementById('calEventDescription').value = '';
    document.getElementById('calEventAllDay').checked = false;
    document.getElementById('calEventStartDateTime').value = '';
    document.getElementById('calEventEndDateTime').value = '';
    document.getElementById('calEventStartDate').value = '';
    document.getElementById('calEventEndDate').value = '';
    toggleCalendarAllDay();
    const status = document.getElementById('calendarEventStatus');
    if (status) status.classList.add('hidden');

    const calSelect = document.getElementById('calEventCalendar');
    calSelect.innerHTML = '<option value="">Loading calendars…</option>';
    fetch(apiUrl('/api/calendars'))
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                calSelect.innerHTML = `<option value="">${escapeHtml(data.error)}</option>`;
                return;
            }
            const calendars = data.calendars || [];
            if (calendars.length === 0) {
                calSelect.innerHTML = '<option value="">No calendars found in Home Assistant</option>';
                return;
            }
            calSelect.innerHTML = calendars.map(c =>
                `<option value="${escapeHtml(c.entity_id)}">${escapeHtml(c.name)}</option>`
            ).join('');
        })
        .catch(() => {
            calSelect.innerHTML = '<option value="">Couldn\'t load calendars — try again</option>';
        });

    const channelSelect = document.getElementById('calEventChannelSelect');
    channelSelect.innerHTML = '<option value="">Loading channels…</option>';
    fetch(apiUrl('/api/channels'))
        .then(r => r.json())
        .then(channels => {
            channelSelect.innerHTML = (channels || []).map(ch =>
                `<option value="${escapeHtml(ch.slug)}"${ch.slug === currentChannel ? ' selected' : ''}>${escapeHtml(ch.icon)} ${escapeHtml(ch.name)}</option>`
            ).join('');
        })
        .catch(() => {
            channelSelect.innerHTML = '<option value="">Couldn\'t load channels</option>';
        });
}

function closeCalendarModal() {
    const modal = document.getElementById('calendarModal');
    if (modal) modal.classList.add('hidden');
}

function toggleCalendarAllDay() {
    const allDay = document.getElementById('calEventAllDay').checked;
    document.getElementById('calEventTimedFields').classList.toggle('hidden', allDay);
    document.getElementById('calEventAllDayFields').classList.toggle('hidden', !allDay);
}

// datetime-local inputs give "2026-08-18T14:00" — Home Assistant's
// calendar.create_event wants "2026-08-18 14:00:00" (a space instead of
// "T", plus explicit seconds).
function formatDateTimeLocalForHa(value) {
    if (!value) return '';
    return value.replace('T', ' ') + ':00';
}

function submitCalendarEvent() {
    const title = document.getElementById('calEventTitle').value.trim();
    const allDay = document.getElementById('calEventAllDay').checked;
    const location = document.getElementById('calEventLocation').value.trim();
    const description = document.getElementById('calEventDescription').value.trim();
    const entity_id = document.getElementById('calEventCalendar').value;
    const channel = document.getElementById('calEventChannelSelect').value;

    if (!title) {
        alert('Give the appointment a title.');
        return;
    }
    if (!entity_id) {
        alert('Choose a calendar.');
        return;
    }

    let start, end;
    if (allDay) {
        start = document.getElementById('calEventStartDate').value;
        end = document.getElementById('calEventEndDate').value;
        if (!start) {
            alert('Choose a start date.');
            return;
        }
    } else {
        start = formatDateTimeLocalForHa(document.getElementById('calEventStartDateTime').value);
        end = formatDateTimeLocalForHa(document.getElementById('calEventEndDateTime').value);
        if (!start || !end) {
            alert('Choose a start and end time.');
            return;
        }
    }

    fetch(apiUrl('/api/calendar/create-event'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, all_day: allDay, start, end, location, description, entity_id, channel })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            closeCalendarModal();
            // Refreshes the sidebar panel immediately rather than
            // waiting for its own periodic/manual refresh — we know
            // exactly when something just got added, no reason to make
            // the person go find the refresh button themselves.
            loadUpcomingEvents();
        })
        .catch(() => alert("Couldn't add that to the calendar. Please try again."));
}

// Renders the "Upcoming" panel at the bottom of the member list — real
// Home Assistant calendar events (from every calendar, not just what's
// come through this app), sorted by when they actually happen.
// --- Mention badges ---
// Shows, per channel, how many @mentions are still unread there — a
// small red count next to the channel name, matching the visual
// language of the jump-to-bottom button's own badge. The count itself
// lives server-side (see api_unread_mention_counts()/mark-read), not
// just tracked in memory here, so it survives a reload and isn't lost
// if a mention happened while this device wasn't even connected.

function refreshMentionBadges() {
    // Cache-busted the same way loadUpcomingEvents() is, and arguably
    // more important here: this runs on a 30-second timer hitting the
    // exact same URL every time. If anything along the way (HA's
    // ingress layer has a known history here) ever decided to cache
    // that URL's response, every single poll after the first would
    // silently keep re-serving the same stale answer — the entire
    // point of polling for freshness, defeated.
    fetch(apiUrl(`/api/mentions/unread-counts?_=${Date.now()}`))
        .then(r => r.json())
        .then(counts => {
            if (counts.error) return; // not accessed through HA, or similar — just leave badges as they are
            document.querySelectorAll('[data-mention-badge]').forEach(badge => {
                const channel = badge.dataset.mentionBadge;
                const count = counts[channel] || 0;
                if (count > 0) {
                    badge.textContent = count > 9 ? '9+' : String(count);
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            });
        })
        .catch(() => {}); // badges just don't update this round — not worth surfacing an error for
}

// Bold channel name for "something new happened here" — deliberately a
// separate, plainer signal from the numbered mention badge above,
// matching how Discord/Slack keep "unread" and "you were mentioned"
// visually distinct rather than conflating them into one indicator.
function refreshUnreadChannelIndicators() {
    // Same cache-busting reasoning as refreshMentionBadges() just above
    // — this runs on the same timer, hitting the same URL repeatedly.
    fetch(apiUrl(`/api/channels/unread-status?_=${Date.now()}`))
        .then(r => r.json())
        .then(unreadChannels => {
            if (!Array.isArray(unreadChannels)) return;
            const unreadSet = new Set(unreadChannels);
            document.querySelectorAll('.channel[data-channel]').forEach(el => {
                el.classList.toggle('has-unread', unreadSet.has(el.dataset.channel));
            });
        })
        .catch(() => {});
}

// The single entry point every touchpoint (page load, channel switch,
// the periodic poll, a live message in the active channel) should call
// — keeps mention badges and the general unread indicator refreshing
// together in lockstep rather than needing two calls wired in
// everywhere.
function refreshChannelIndicators() {
    refreshMentionBadges();
    refreshUnreadChannelIndicators();
}

function markChannelRead(channel) {
    if (!channel) return;
    // Updated immediately rather than waiting on the request to
    // complete — nothing about "you're looking at this channel right
    // now" needs to wait on a round-trip to feel correct. Covers both
    // indicators since the one server call now clears both (see
    // mark_channel_read() server-side).
    const badge = document.querySelector(`[data-mention-badge="${CSS.escape(channel)}"]`);
    if (badge) badge.classList.add('hidden');
    const channelEl = document.querySelector(`.channel[data-channel="${CSS.escape(channel)}"]`);
    if (channelEl) channelEl.classList.remove('has-unread');

    fetch(apiUrl('/api/mentions/mark-read'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel })
    }).catch(() => {});
}

function loadUpcomingEvents() {
    const list = document.getElementById('upcomingEventsList');
    if (!list) return; // panel isn't rendered at all when calendar_enabled is false

    // The server already sends Cache-Control: no-store on this response,
    // but that's not always enough — Home Assistant's ingress iframe
    // layer has a history of not reliably honoring cache-control headers
    // for in-page fetches (see set_cache_headers() server-side). A
    // timestamp query param makes every request URL unique instead, so
    // there's simply nothing for any cache in that path to match against,
    // regardless of whether it's respecting headers correctly. This used
    // to also set the fetch-level `cache: 'no-store'` option on top —
    // removed after it turned out to make things worse rather than
    // better on at least one real session (this panel, and avatars in
    // the message list, stopped loading at all rather than just being
    // stale). The URL uniqueness alone is doing the actual work here.
    fetch(apiUrl(`/api/calendar/upcoming?_=${Date.now()}`))
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                list.innerHTML = `<p class="settings-hint">${escapeHtml(data.error)}</p>`;
                return;
            }
            const events = data.events || [];
            if (events.length === 0) {
                list.innerHTML = '<p class="settings-hint">Nothing on the calendar yet.</p>';
                return;
            }
            list.innerHTML = events.map(buildUpcomingEventItemHtml).join('');
        })
        .catch(() => {
            list.innerHTML = '<p class="settings-hint">Couldn\'t load the calendar.</p>';
        });
}

function buildUpcomingEventItemHtml(event) {
    const startDate = new Date(event.all_day ? event.start + 'T00:00:00' : event.start.replace(' ', 'T'));
    const month = startDate.toLocaleDateString(undefined, { month: 'short' });
    const day = startDate.getDate();

    let metaParts = [];
    if (event.all_day) {
        metaParts.push('All day');
    } else {
        metaParts.push(startDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }));
    }
    metaParts.push(event.calendar_name);
    if (event.added_by) metaParts.push(`Added by ${event.added_by}`);

    return `
        <div class="upcoming-event-item" data-event-payload="${escapeHtml(JSON.stringify(event))}" role="button" tabindex="0" title="${escapeHtml(event.title)}${event.location ? ' — ' + escapeHtml(event.location) : ''}">
            <div class="upcoming-event-date">
                <span class="month">${escapeHtml(month)}</span>
                <span class="day">${day}</span>
            </div>
            <div class="upcoming-event-details">
                <div class="upcoming-event-title">${escapeHtml(event.title)}</div>
                <div class="upcoming-event-meta">${escapeHtml(metaParts.join(' · '))}</div>
            </div>
        </div>
    `;
}

// Shared by the calendar_event message card and the details modal —
// the richer of the two "when" formats already in this app (weekday +
// month + day, plus a time range for anything that isn't all-day).
// buildUpcomingEventItemHtml() intentionally keeps its own, more
// compact month/day format instead of this one — that's a deliberate
// difference for the tight sidebar list, not something worth unifying.
function formatEventWhen(event) {
    let when = '';
    if (event.all_day && event.start) {
        const startDate = new Date(event.start + 'T00:00:00');
        when = startDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
        if (event.end) {
            const endDateExclusive = new Date(event.end + 'T00:00:00');
            const lastDay = new Date(endDateExclusive.getTime() - 86400000);
            if (lastDay.getTime() !== startDate.getTime()) {
                when += ' – ' + lastDay.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
            }
        }
    } else if (event.start) {
        const start = new Date(event.start.replace(' ', 'T'));
        when = start.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
            + ' · ' + start.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
        if (event.end) {
            const end = new Date(event.end.replace(' ', 'T'));
            when += ' – ' + end.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
        }
    }
    return when;
}

// The client-side counterpart to summarize_message_for_notification()
// server-side — kept as its own function rather than shared, since
// this one runs for every message as it's rendered (any message might
// later get replied to), while the server-side version only runs once,
// at reply-send time. Deliberately mirrors the same logic/thresholds
// so a reply's preview reads the same whether it was just typed or
// loaded from history.
function summarizeMessageForReply(data, msgType) {
    if (msgType === 'calendar_event') {
        let event;
        try {
            event = JSON.parse(data.content);
        } catch (e) {
            return 'Added a calendar event';
        }
        const when = formatEventWhen(event);
        const title = event.title || 'Untitled event';
        return when ? `📅 ${title} — ${when}` : `📅 ${title}`;
    }
    const content = (data.content || '').trim();
    if (content) {
        return content.length <= 200 ? content : content.slice(0, 197) + '…';
    }
    if (msgType === 'gif') return 'Sent a GIF';
    if (msgType === 'image') return 'Sent a photo';
    if (msgType === 'video') return 'Sent a video';
    if (msgType === 'file') {
        const name = data.file?.filename || data.file_name;
        return name ? `Shared ${name}` : 'Shared a file';
    }
    return 'Sent a message';
}

// Details modal shared by both places a calendar event can be clicked
// — the calendar_event card in the message feed, and an entry in the
// Upcoming panel — since both hand it a plain object with the same
// core shape (title/start/end/all_day/location, and where available,
// entity_id/calendar_name/description/added_by). Fields that aren't
// present (older calendar_event messages posted before this was added,
// for instance) are simply omitted from the rendered rows rather than
// showing an empty placeholder.
function openCalendarEventDetails(event) {
    const modal = document.getElementById('calendarEventDetailsModal');
    const content = document.getElementById('calendarEventDetailsContent');
    if (!modal || !content) return;

    const when = formatEventWhen(event);
    const rows = [];
    if (when) rows.push({ icon: '🕐', text: when });
    if (event.location) rows.push({ icon: '📍', text: event.location });
    if (event.calendar_name) rows.push({ icon: '📅', text: event.calendar_name });
    if (event.added_by) rows.push({ icon: '👤', text: `Added by ${event.added_by}` });

    content.innerHTML = `
        <div class="calendar-event-details-title">${escapeHtml(event.title || 'Untitled event')}</div>
        ${rows.map(r => `<div class="calendar-event-details-row"><span>${r.icon}</span><span>${escapeHtml(r.text)}</span></div>`).join('')}
        ${event.description ? `<div class="calendar-event-details-description">${escapeHtml(event.description)}</div>` : ''}
    `;
    modal.classList.remove('hidden');
}

function closeCalendarEventDetails() {
    const modal = document.getElementById('calendarEventDetailsModal');
    if (modal) modal.classList.add('hidden');
}

// Delegated rather than an inline onclick — both card types already
// carry their full data in a data-event-payload attribute (see
// buildCalendarEventHtml() and buildUpcomingEventItemHtml()), so a
// single document-level listener can open the same modal for either,
// the same pattern .reaction pills already use elsewhere in this app.
document.addEventListener('click', (e) => {
    const target = e.target.closest('.calendar-event-card, .upcoming-event-item');
    if (!target) return;
    const payload = target.dataset.eventPayload;
    if (!payload) return;
    try {
        openCalendarEventDetails(JSON.parse(payload));
    } catch (err) {}
});

// Renders a calendar_event message's JSON payload (see
// api_create_calendar_event() server-side) as a small card rather than
// a wall of text. Falls back to plain escaped text if the payload isn't
// valid JSON for any reason — old/corrupted data should never crash
// the message list, just look a little plainer.
function buildCalendarEventHtml(content) {
    let event;
    try {
        event = JSON.parse(content);
    } catch (e) {
        return `<div class="message-text">${escapeHtml(content || '')}</div>`;
    }

    const title = event.title || 'Untitled event';
    const when = formatEventWhen(event);

    // The raw payload is round-tripped back out through a data
    // attribute (HTML-escaped, same as any other user-influenced value
    // going into an attribute) rather than interpolated into an
    // onclick="..." string — a title or location containing a quote
    // could otherwise break out of the attribute. openCalendarEventDetails()
    // is wired up via delegated click listener, not an inline handler,
    // matching how .reaction pills already work in this app.
    return `
        <div class="calendar-event-card" data-event-payload="${escapeHtml(content)}" role="button" tabindex="0">
            <div class="calendar-event-icon">📅</div>
            <div>
                <div class="calendar-event-title">${escapeHtml(title)}</div>
                ${when ? `<div class="calendar-event-when">${escapeHtml(when)}</div>` : ''}
                ${event.location ? `<div class="calendar-event-location">📍 ${escapeHtml(event.location)}</div>` : ''}
            </div>
        </div>
    `;
}

function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.querySelectorAll('.settings-panel').forEach(p => {
        p.classList.toggle('active', p.id === `settingsPanel-${tab}`);
    });
    if (tab === 'emojis') loadCustomEmojiList();
    // Without this, switching to Channels after the modal's initial
    // open (which only ever runs once, in openMySettings()) left both
    // the channel list and the category dropdown permanently stuck on
    // whatever they showed the very first time — including "Loading
    // categories…" forever if that first load happened to be slow or
    // failed.
    if (tab === 'channels') loadChannelsSettings();
}

function openMySettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('hidden');

    // Always open on the Profile tab rather than remembering whichever
    // tab was open last — predictable beats clever here, and the other
    // tabs are one click away regardless.
    switchSettingsTab('profile');

    fetch(apiUrl('/api/me'))
        .then(r => r.json())
        .then(me => {
            const input = document.getElementById('myAliasInput');
            const hint = document.getElementById('myHaNameHint');
            if (input) input.value = me.alias || '';
            if (hint) hint.textContent = `(your Home Assistant name is "${me.ha_name}")`;
            setAvatarPreview(me.avatar_url);
        })
        .catch(() => {});

    loadNotifySettings();
    loadChannelsSettings();
}

function loadNotifySettings() {
    const select = document.getElementById('notifyServiceSelect');
    const channelList = document.getElementById('notifyChannelList');
    const status = document.getElementById('notifySaveStatus');
    if (!select || !channelList) return;

    if (status) status.classList.add('hidden');
    select.innerHTML = '<option value="">Loading devices…</option>';
    channelList.innerHTML = '<p class="settings-hint">Loading channels…</p>';

    Promise.all([
        fetch(apiUrl('/api/notify/services')).then(r => r.json()),
        fetch(apiUrl('/api/notify/prefs')).then(r => r.json()),
        fetch(apiUrl('/api/channels')).then(r => r.json())
    ])
        .then(([servicesData, prefs, channels]) => {
            const services = servicesData.services || [];

            if (servicesData.error) {
                select.innerHTML = `<option value="">${escapeHtml(servicesData.error)}</option>`;
            } else if (services.length === 0) {
                select.innerHTML = '<option value="">No devices found — open the Home Assistant Companion App on your phone first</option>';
            } else {
                select.innerHTML = '<option value="">Choose a device…</option>' +
                    services.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
                if (prefs.notify_service) select.value = prefs.notify_service;
            }

            const subscribed = new Set(prefs.channels || []);
            if (!channels || channels.length === 0) {
                channelList.innerHTML = '<p class="settings-hint">No channels yet.</p>';
                return;
            }
            channelList.innerHTML = channels.map(ch => `
                <label class="settings-toggle-label">
                    <input type="checkbox" class="notify-channel-checkbox" value="${escapeHtml(ch.slug)}" ${subscribed.has(ch.slug) ? 'checked' : ''}>
                    ${escapeHtml(ch.icon)} ${escapeHtml(ch.name)}
                </label>
            `).join('');
        })
        .catch(() => {
            select.innerHTML = '<option value="">Couldn\'t load devices — try again</option>';
            channelList.innerHTML = '<p class="settings-hint">Couldn\'t load channels — try again.</p>';
        });
}

function saveNotifyPrefs() {
    const select = document.getElementById('notifyServiceSelect');
    const status = document.getElementById('notifySaveStatus');
    const notify_service = select ? select.value : '';
    const channels = Array.from(document.querySelectorAll('.notify-channel-checkbox:checked')).map(cb => cb.value);

    if (channels.length > 0 && !notify_service) {
        alert('Choose a device before subscribing to any channels.');
        return;
    }

    fetch(apiUrl('/api/notify/prefs'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notify_service, channels })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            // Deliberately does NOT close the settings modal — the
            // device dropdown and channel list need to stay reachable so
            // changing your mind is just "tick a different box, Save
            // again", not "reopen Settings from scratch".
            if (status) {
                status.textContent = 'Saved';
                status.classList.remove('hidden');
            }
        })
        .catch(() => alert("Couldn't save notification settings. Please try again."));
}

function sendTestNotification() {
    const select = document.getElementById('notifyServiceSelect');
    const notify_service = select ? select.value : '';
    if (!notify_service) {
        alert('Choose a device first.');
        return;
    }

    fetch(apiUrl('/api/notify/test'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notify_service })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('Test notification sent — check your phone.');
            }
        })
        .catch(() => alert("Couldn't send a test notification."));
}

function loadChannelsSettings() {
    const list = document.getElementById('settingsChannelList');
    if (!list) return;
    list.innerHTML = '<p class="settings-hint">Loading channels…</p>';

    const canManage = window.IS_ADMIN || window.IS_OWNER;

    fetch(apiUrl('/api/channels'))
        .then(r => r.json())
        .then(channels => {
            if (!channels || channels.length === 0) {
                list.innerHTML = '<p class="settings-hint">No channels yet.</p>';
                return;
            }
            list.innerHTML = channels.map((ch, idx, arr) => {
                // A channel only ever reorders among its own category's
                // siblings, so "first/last" here means first/last WITHIN
                // that category, not first/last in this flat list overall
                // — checked by comparing against the neighboring entry's
                // own category_id, since channels sharing a category are
                // always grouped consecutively in what /api/channels returns.
                const isFirstInCategory = idx === 0 || arr[idx - 1].category_id !== ch.category_id;
                const isLastInCategory = idx === arr.length - 1 || arr[idx + 1].category_id !== ch.category_id;
                return `
                <div class="settings-channel-row">
                    <span>${escapeHtml(ch.icon)}</span>
                    <span style="flex:1;">${escapeHtml(ch.name)}</span>
                    ${canManage ? `
                        <button class="settings-reorder-btn" onclick="moveChannelSettings('${escapeHtml(ch.slug)}', 'up')" title="Move up"${isFirstInCategory ? ' disabled' : ''}>▲</button>
                        <button class="settings-reorder-btn" onclick="moveChannelSettings('${escapeHtml(ch.slug)}', 'down')" title="Move down"${isLastInCategory ? ' disabled' : ''}>▼</button>
                        <button class="settings-channel-delete" onclick="deleteChannelSettings('${escapeHtml(ch.slug)}')" title="Delete channel"${channels.length <= 1 ? ' disabled' : ''}>✕</button>
                    ` : ''}
                </div>
            `;
            }).join('');
        })
        .catch(() => {
            list.innerHTML = '<p class="settings-hint">Couldn\'t load channels.</p>';
        });

    loadChannelCategoriesForAddForm();
    loadCategoriesSettings();
}

// Categories themselves aren't creatable or deletable from here (that
// stays admin-panel-only, see admin_add_category/admin_delete_category
// on the server) — this is purely for reordering, which is owner/admin
// like channel management, not admin-only like creating one.
function loadCategoriesSettings() {
    const list = document.getElementById('settingsCategoryList');
    if (!list) return;
    list.innerHTML = '<p class="settings-hint">Loading categories…</p>';

    const canManage = window.IS_ADMIN || window.IS_OWNER;

    fetch(apiUrl('/api/categories'))
        .then(r => r.json())
        .then(categories => {
            if (!categories || categories.length === 0) {
                list.innerHTML = '<p class="settings-hint">No categories yet.</p>';
                return;
            }
            list.innerHTML = categories.map((cat, idx, arr) => `
                <div class="settings-channel-row">
                    <span style="flex:1;">${escapeHtml(cat.name)}</span>
                    ${canManage ? `
                        <button class="settings-reorder-btn" onclick="moveCategorySettings(${cat.id}, 'up')" title="Move up"${idx === 0 ? ' disabled' : ''}>▲</button>
                        <button class="settings-reorder-btn" onclick="moveCategorySettings(${cat.id}, 'down')" title="Move down"${idx === arr.length - 1 ? ' disabled' : ''}>▼</button>
                    ` : ''}
                </div>
            `).join('');
        })
        .catch(() => {
            list.innerHTML = '<p class="settings-hint">Couldn\'t load categories.</p>';
        });
}

function moveChannelSettings(slug, direction) {
    fetch(apiUrl('/api/channels/move'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, direction })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadChannelsSettings();
            rebuildChannelSidebar(data.channels);
        })
        .catch(() => alert("Couldn't move the channel. Please try again."));
}

function moveCategorySettings(categoryId, direction) {
    fetch(apiUrl('/api/categories/move'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_id: categoryId, direction })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadCategoriesSettings();
            rebuildChannelSidebar(data.channels);
        })
        .catch(() => alert("Couldn't move the category. Please try again."));
}

// Rebuilds the sidebar's channel-list section from scratch against a
// fresh, authoritative channel list — needed after a reorder, since
// the sidebar is otherwise only ever built once, server-side, at page
// load, with no client-side path for re-sorting what's already there
// (addChannelToSidebar only ever appends one new entry in place).
function rebuildChannelSidebar(channels) {
    const channelList = document.querySelector('.channel-sidebar .channel-list');
    if (!channelList) return;

    // Group into the same category-ordered structure the server-side
    // template produces, using each category's own first appearance in
    // this already category-ordered list to preserve category order
    // without needing a separate /api/categories round-trip here.
    const categoryOrder = [];
    const byCategoryId = {};
    channels.forEach(ch => {
        if (!byCategoryId[ch.category_id]) {
            byCategoryId[ch.category_id] = { name: ch.category_name, channels: [] };
            categoryOrder.push(ch.category_id);
        }
        byCategoryId[ch.category_id].channels.push(ch);
    });

    channelList.innerHTML = categoryOrder.map(catId => {
        const cat = byCategoryId[catId];
        const channelsHtml = cat.channels.map(ch => `
            <div class="channel${ch.slug === currentChannel ? ' active' : ''}" data-channel="${escapeHtml(ch.slug)}">
                <span class="channel-icon">${escapeHtml(ch.icon)}</span>
                <span class="channel-name">${escapeHtml(ch.name)}</span>
                <span class="mention-badge hidden" data-mention-badge="${escapeHtml(ch.slug)}"></span>
            </div>
        `).join('');
        return `<div class="category">${escapeHtml(cat.name)}</div><div class="category-channels" data-category-id="${catId}">${channelsHtml}</div>`;
    }).join('');

    // innerHTML replacement drops any previously-attached listeners —
    // re-wire clicks on the fresh elements, same handler switchChannel()
    // click binding uses everywhere else channels get created.
    channelList.querySelectorAll('.channel').forEach(el => {
        el.addEventListener('click', function() {
            switchChannel(this.dataset.channel);
        });
    });

    // Badge/unread state isn't part of what /api/channels returns, so
    // it has to be re-fetched and reapplied after the rebuild rather
    // than preserved through it.
    refreshChannelIndicators();
}

// Populates the category dropdown in the "Add a channel" form — a
// channel always needs a real, existing category to belong to, so this
// has to be current every time the form could be used, not just
// fetched once at page load.
function loadChannelCategoriesForAddForm() {
    const select = document.getElementById('newChannelCategory');
    if (!select) return;
    select.innerHTML = '<option value="">Loading categories…</option>';

    fetch(apiUrl('/api/categories'))
        .then(r => r.json())
        .then(categories => {
            if (!categories || categories.length === 0) {
                // Shouldn't actually happen — the server always keeps at
                // least one category — but a channel truly cannot be
                // added without one, so this is the honest state to show
                // if it somehow ever does.
                select.innerHTML = '<option value="">No categories yet — ask an admin to add one</option>';
                return;
            }
            select.innerHTML = '<option value="">Choose a category…</option>' +
                categories.map(cat => `<option value="${cat.id}">${escapeHtml(cat.name)}</option>`).join('');
        })
        .catch(() => {
            select.innerHTML = '<option value="">Couldn\'t load categories — try again</option>';
        });
}

function deleteChannelSettings(slug) {
    if (!confirm(`Delete #${slug}? Its messages are hidden, not erased, and come back if a channel with the same name is added again.`)) return;

    fetch(apiUrl('/api/channels/delete'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadChannelsSettings();
            loadNotifySettings(); // it may have been someone's subscribed channel
            removeChannelFromSidebar(slug, data.channels || []);
        })
        .catch(() => alert("Couldn't delete the channel. Please try again."));
}

function removeChannelFromSidebar(slug, remainingChannels) {
    const el = document.querySelector(`.channel-sidebar .channel[data-channel="${CSS.escape(slug)}"]`);
    const wasActive = el && el.classList.contains('active');
    if (el) el.remove();

    // If the channel you were actively viewing is the one just deleted,
    // land somewhere that still exists instead of showing a channel
    // that's no longer in the sidebar.
    if (wasActive && remainingChannels.length > 0) {
        switchChannel(remainingChannels[0].slug);
    }
}

// Sidebar channel elements each get their own click listener at page
// load (see initializeChat()), not a delegated one — so a channel added
// without a full page reload needs the same treatment here to actually
// be clickable.
function addChannelToSidebar(ch) {
    // Channels are now grouped by category in the sidebar (see
    // index.html) — this has to land in the right category's own
    // container, not just get appended to a flat list the way it used
    // to. The category itself is guaranteed to already be there: a
    // channel can only ever be added into a category that already
    // exists, and the sidebar renders every category server-side at
    // page load.
    const categoryGroup = document.querySelector(`.category-channels[data-category-id="${ch.category_id}"]`);
    if (!categoryGroup) return;
    if (categoryGroup.querySelector(`.channel[data-channel="${CSS.escape(ch.slug)}"]`)) return;

    const el = document.createElement('div');
    el.className = 'channel';
    el.dataset.channel = ch.slug;
    el.innerHTML = `<span class="channel-icon">${escapeHtml(ch.icon)}</span><span class="channel-name">${escapeHtml(ch.name)}</span><span class="mention-badge hidden" data-mention-badge="${escapeHtml(ch.slug)}"></span>`;
    el.addEventListener('click', function() {
        switchChannel(this.dataset.channel);
    });
    categoryGroup.appendChild(el);
}

function addChannel() {
    const iconInput = document.getElementById('newChannelIcon');
    const nameInput = document.getElementById('newChannelName');
    const categorySelect = document.getElementById('newChannelCategory');
    const status = document.getElementById('addChannelStatus');
    const icon = iconInput ? iconInput.value.trim() : '';
    const name = nameInput ? nameInput.value.trim() : '';
    const category_id = categorySelect ? categorySelect.value : '';

    if (!name) {
        alert('Give the channel a name first.');
        return;
    }
    if (!category_id) {
        alert('Choose a category first.');
        return;
    }

    fetch(apiUrl('/api/channels/add'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, icon, category_id })
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            if (nameInput) nameInput.value = '';
            if (iconInput) iconInput.value = '';
            if (status) {
                status.textContent = `Added #${name}`;
                status.classList.remove('hidden');
            }
            loadChannelsSettings();
            // The new channel should be immediately selectable in the
            // notification tab's per-channel list too.
            loadNotifySettings();
            const added = (data.channels || []).find(c => c.slug === data.slug);
            if (added) addChannelToSidebar(added);
        })
        .catch(() => alert("Couldn't add the channel. Please try again."));
}

function closeMySettings() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('hidden');
}

function saveMyAlias() {
    const input = document.getElementById('myAliasInput');
    const alias = input ? input.value.trim() : '';

    fetch(apiUrl('/api/my-alias'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alias })
    })
        .then(r => r.json())
        .then(() => {
            // Reload so the new name applies everywhere at once — the
            // sidebar, the header, and every past message you've sent.
            forceFreshReload();
        })
        .catch(() => {
            alert("Couldn't save your display name. Please try again.");
        });
}

// Current avatar as last loaded from /api/me — lets removeMyAvatar() know
// whether there's actually anything to remove without a round-trip.
let myCurrentAvatarUrl = '';

function setAvatarPreview(avatarUrl) {
    myCurrentAvatarUrl = avatarUrl || '';
    const preview = document.getElementById('myAvatarPreview');
    const removeBtn = document.getElementById('removeAvatarBtn');
    if (preview) preview.innerHTML = avatarInnerHtml(myCurrentAvatarUrl, currentUser);
    if (removeBtn) removeBtn.classList.toggle('hidden', !myCurrentAvatarUrl);
}

function uploadMyAvatar(event) {
    const fileInput = event.target;
    const file = fileInput.files[0];
    if (!file) return;

    // GIFs skip the cropper entirely and upload as-is — cropping means
    // rendering to a canvas, which only ever captures a single static
    // frame and would silently strip the animation from an animated
    // avatar. Everything else (PNG/JPEG/WEBP) goes through cropping.
    if (file.type === 'image/gif') {
        submitAvatarFile(file, fileInput);
        return;
    }

    openAvatarCropper(file, fileInput);
}

function submitAvatarFile(file, fileInputToReset) {
    const formData = new FormData();
    // A real File (the GIF-bypass path) already carries its own
    // filename; a bare Blob (canvas.toBlob()'s output, from the crop
    // flow) doesn't, and would otherwise default to the generic name
    // "blob" — giving it a real one is purely for clarity/debugging,
    // not correctness, since the server derives the saved extension
    // from the declared mimetype either way, never the filename.
    formData.append('file', file, file.name || 'avatar-cropped.png');

    fetch(apiUrl('/api/my-avatar'), {
        method: 'POST',
        body: formData
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            // Reload so the new photo applies everywhere at once — the
            // sidebar, the header, and every past message you've sent —
            // same reasoning as saveMyAlias() above.
            forceFreshReload();
        })
        .catch(() => alert("Couldn't upload your avatar. Please try again."))
        .finally(() => { if (fileInputToReset) fileInputToReset.value = ''; });
}

// --- Avatar cropper ---
// A fixed-size circular viewport (see .avatar-crop-viewport in CSS) onto
// an image the person can drag to reposition and zoom to scale, always
// kept large enough to fully cover the viewport (no gaps). All position
// state below is in "already scaled" CSS pixels — offsetX/offsetY are
// where the image's top-left corner sits relative to the viewport's,
// not raw image coordinates.
let avatarCropState = null; // null when the modal isn't open
let avatarCropDrag = null; // null when not actively dragging
const AVATAR_CROP_VIEWPORT_SIZE = 280;
const AVATAR_CROP_MAX_ZOOM_MULTIPLIER = 3;
const AVATAR_CROP_OUTPUT_SIZE = 400;

function openAvatarCropper(file, fileInputToReset) {
    const modal = document.getElementById('avatarCropModal');
    const img = document.getElementById('avatarCropImage');
    if (!modal || !img) return;

    const objectUrl = URL.createObjectURL(file);
    img.src = objectUrl;
    img.onerror = () => {
        // Without this, a corrupted file or a format quirk that passes
        // the file input's accept filter but isn't actually decodable
        // fails completely silently — the modal never opens, nothing
        // tells the person anything went wrong, and the object URL
        // leaks since nothing ever revokes it.
        URL.revokeObjectURL(objectUrl);
        img.onload = null;
        img.onerror = null;
        if (fileInputToReset) fileInputToReset.value = '';
        alert("Couldn't open that image. Please try a different photo.");
    };
    img.onload = () => {
        img.onerror = null;
        const minScale = AVATAR_CROP_VIEWPORT_SIZE / Math.min(img.naturalWidth, img.naturalHeight);
        avatarCropState = {
            file,
            fileInputToReset,
            objectUrl,
            naturalWidth: img.naturalWidth,
            naturalHeight: img.naturalHeight,
            minScale,
            scale: minScale,
            // Centered by default — the dimension that overflows the
            // viewport (whichever one isn't the constraining one that
            // minScale was based on) starts evenly split on both sides.
            offsetX: (AVATAR_CROP_VIEWPORT_SIZE - img.naturalWidth * minScale) / 2,
            offsetY: (AVATAR_CROP_VIEWPORT_SIZE - img.naturalHeight * minScale) / 2,
        };
        const zoomSlider = document.getElementById('avatarCropZoom');
        if (zoomSlider) zoomSlider.value = 0;
        renderAvatarCropTransform();
        modal.classList.remove('hidden');
    };
}

function clampAvatarCropOffsets(state) {
    const displayedWidth = state.naturalWidth * state.scale;
    const displayedHeight = state.naturalHeight * state.scale;
    // Image edges can never pull inward past the viewport edges — right
    // edge must reach at least the viewport's right side, left edge can
    // never be right of the viewport's left side, and so on for top/bottom.
    state.offsetX = Math.min(0, Math.max(AVATAR_CROP_VIEWPORT_SIZE - displayedWidth, state.offsetX));
    state.offsetY = Math.min(0, Math.max(AVATAR_CROP_VIEWPORT_SIZE - displayedHeight, state.offsetY));
}

function renderAvatarCropTransform() {
    if (!avatarCropState) return;
    const img = document.getElementById('avatarCropImage');
    if (!img) return;
    clampAvatarCropOffsets(avatarCropState);
    img.style.width = `${avatarCropState.naturalWidth * avatarCropState.scale}px`;
    img.style.height = `${avatarCropState.naturalHeight * avatarCropState.scale}px`;
    img.style.transform = `translate(${avatarCropState.offsetX}px, ${avatarCropState.offsetY}px)`;
}

function onAvatarCropZoomChange() {
    if (!avatarCropState) return;
    const slider = document.getElementById('avatarCropZoom');
    if (!slider) return;
    const t = Number(slider.value) / 100; // 0..1
    avatarCropState.scale = avatarCropState.minScale * (1 + t * (AVATAR_CROP_MAX_ZOOM_MULTIPLIER - 1));
    // Re-clamping (inside renderAvatarCropTransform) rather than
    // re-centering keeps whatever part of the photo was framed before
    // the zoom change as close to framed as it can still validly be,
    // instead of snapping back to center on every slider move.
    renderAvatarCropTransform();
}

function avatarCropPointerPos(e) {
    if (e.touches && e.touches.length > 0) {
        return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
    return { x: e.clientX, y: e.clientY };
}

function onAvatarCropDragStart(e) {
    if (!avatarCropState) return;
    const pos = avatarCropPointerPos(e);
    avatarCropDrag = {
        startX: pos.x,
        startY: pos.y,
        startOffsetX: avatarCropState.offsetX,
        startOffsetY: avatarCropState.offsetY,
    };
    const viewport = document.getElementById('avatarCropViewport');
    if (viewport) viewport.classList.add('dragging');
    e.preventDefault();
}

function onAvatarCropDragMove(e) {
    if (!avatarCropDrag || !avatarCropState) return;
    const pos = avatarCropPointerPos(e);
    avatarCropState.offsetX = avatarCropDrag.startOffsetX + (pos.x - avatarCropDrag.startX);
    avatarCropState.offsetY = avatarCropDrag.startOffsetY + (pos.y - avatarCropDrag.startY);
    renderAvatarCropTransform();
    e.preventDefault();
}

function onAvatarCropDragEnd() {
    avatarCropDrag = null;
    const viewport = document.getElementById('avatarCropViewport');
    if (viewport) viewport.classList.remove('dragging');
}

function applyAvatarCrop() {
    if (!avatarCropState) return;
    const img = document.getElementById('avatarCropImage');
    if (!img) return;

    // Working backward from the current on-screen transform to figure
    // out which square region of the *original, full-resolution* image
    // is currently visible in the viewport — dividing by scale converts
    // from on-screen (already-scaled) pixels back to natural image
    // pixels.
    const sourceX = -avatarCropState.offsetX / avatarCropState.scale;
    const sourceY = -avatarCropState.offsetY / avatarCropState.scale;
    const sourceSize = AVATAR_CROP_VIEWPORT_SIZE / avatarCropState.scale;

    const canvas = document.createElement('canvas');
    canvas.width = AVATAR_CROP_OUTPUT_SIZE;
    canvas.height = AVATAR_CROP_OUTPUT_SIZE;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, sourceX, sourceY, sourceSize, sourceSize, 0, 0, AVATAR_CROP_OUTPUT_SIZE, AVATAR_CROP_OUTPUT_SIZE);

    const fileInputToReset = avatarCropState.fileInputToReset;
    canvas.toBlob(blob => {
        if (!blob) {
            alert("Couldn't process that image. Please try a different photo.");
            return;
        }
        closeAvatarCropper();
        submitAvatarFile(blob, fileInputToReset);
    }, 'image/png');
}

function closeAvatarCropper() {
    const modal = document.getElementById('avatarCropModal');
    if (modal) modal.classList.add('hidden');
    if (avatarCropState) {
        // Selecting Cancel (rather than Save) still leaves a picked file
        // sitting in the <input> — without resetting it here, choosing
        // the exact same file again afterward wouldn't even fire a
        // change event (browsers only fire "change" when the value
        // actually differs from before), so the cropper would silently
        // fail to reopen.
        if (avatarCropState.fileInputToReset) avatarCropState.fileInputToReset.value = '';
        URL.revokeObjectURL(avatarCropState.objectUrl);
    }
    avatarCropState = null;
    avatarCropDrag = null;
}

function removeMyAvatar() {
    if (!myCurrentAvatarUrl) return;

    fetch(apiUrl('/api/my-avatar'), { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            forceFreshReload();
        })
        .catch(() => alert("Couldn't remove your avatar. Please try again."));
}

function loadCustomEmojiList() {
    const list = document.getElementById('customEmojiList');
    if (!list) return;
    list.innerHTML = '';
    
    Object.entries(customEmojis).forEach(([name, url]) => {
        const item = document.createElement('div');
        item.className = 'custom-emoji-item';
        item.innerHTML = `
            <img src="${safeUrl(resolveUrl(url))}" alt="${escapeHtml(name)}">
            <span>${escapeHtml(name)}</span>
        `;
        list.appendChild(item);
    });
}

function uploadEmoji() {
    const nameInput = document.getElementById('newEmojiName');
    const fileInput = document.getElementById('emojiFileInput');
    
    if (!nameInput || !fileInput) return;
    
    const name = nameInput.value.trim();
    if (!name || !fileInput.files[0]) {
        alert('Please provide a name and image');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name.replace(/:/g, ''));
    formData.append('file', fileInput.files[0]);
    formData.append('created_by', currentUser || 'unknown');
    
    fetch(apiUrl('/api/emoji/upload'), {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            customEmojis[data.name] = data.url;
            loadCustomEmojiList();
            nameInput.value = '';
            fileInput.value = '';
        } else {
            alert(data.error);
        }
    });
}

function openReactionPicker(messageId, btnEl) {
    const picker = document.getElementById('emojiPicker');
    if (!picker) return;
    const gifPicker = document.getElementById('gifPicker');
    if (gifPicker) gifPicker.classList.add('hidden');

    // Clicking the same message's reaction button again closes the
    // picker, same toggle behavior as the composer's emoji button.
    const alreadyOpenForThis = !picker.classList.contains('hidden') &&
        emojiPickerContext && emojiPickerContext.messageId === messageId;
    if (alreadyOpenForThis) {
        hideEmojiPicker();
        return;
    }

    emojiPickerContext = { messageId };
    picker.classList.remove('hidden');

    // Anchor it near the button that was clicked instead of the
    // composer's fixed bottom-right spot, clamped to the viewport so it
    // doesn't get cut off for messages near the top or edges of the
    // screen.
    picker.style.position = 'fixed';
    const rect = btnEl.getBoundingClientRect();
    const margin = 8;
    const width = picker.offsetWidth || 380;
    const height = picker.offsetHeight || 420;

    let left = rect.right - width;
    if (left < margin) left = margin;
    if (left + width > window.innerWidth - margin) left = window.innerWidth - width - margin;

    let top = rect.bottom + margin;
    if (top + height > window.innerHeight - margin) top = rect.top - height - margin;
    if (top < margin) top = margin;

    picker.style.left = `${left}px`;
    picker.style.top = `${top}px`;
    picker.style.right = 'auto';
    picker.style.bottom = 'auto';

    clearEmojiSearchInput();
    switchEmojiTabProgrammatic('recent');
}

// switchEmojiTab() reads `event.target`, which only exists for a real
// click — calling it programmatically (no click event) would throw.
// This does the same tab-switch without relying on a click event.
function switchEmojiTabProgrammatic(category) {
    document.querySelectorAll('.emoji-tab').forEach(t => t.classList.remove('active'));
    const tab = document.querySelector(`.emoji-tab[onclick="switchEmojiTab('${category}')"]`);
    if (tab) tab.classList.add('active');
    currentEmojiCategory = category;
    loadEmojiCategory(category);
}

function toggleReaction(messageId, emoji) {
    socket.emit('add_reaction', {
        message_id: messageId,
        emoji: emoji,
        user: currentUser
    });
}

function deleteMessage(messageId) {
    if (!confirm('Delete this message? This can\'t be undone.')) return;
    socket.emit('delete_message', { message_id: messageId });
}

function removeMessageFromDom(messageId) {
    const el = document.querySelector(`.message[data-id="${messageId}"]`);
    if (el) el.remove();
    delete messageReactions[messageId];
}

function updateReaction(messageId, emoji, user, added) {
    if (!messageReactions[messageId]) messageReactions[messageId] = {};
    const bucket = messageReactions[messageId];

    if (added) {
        if (!bucket[emoji]) bucket[emoji] = [];
        if (!bucket[emoji].includes(user)) bucket[emoji].push(user);
    } else if (bucket[emoji]) {
        bucket[emoji] = bucket[emoji].filter(u => u !== user);
        if (bucket[emoji].length === 0) delete bucket[emoji];
    }

    renderMessageReactions(messageId);
}

function openImageViewer(url) {
    const viewer = document.getElementById('imageViewer');
    const img = document.getElementById('viewerImage');
    if (viewer && img) {
        img.src = url;
        viewer.classList.remove('hidden');
    }
}

function closeImageViewer() {
    const viewer = document.getElementById('imageViewer');
    if (viewer) viewer.classList.add('hidden');
}

function addToSharedMedia(url) {
    const grid = document.getElementById('sharedMedia');
    if (!grid) return;
    
    const safe = safeUrl(url);
    const item = document.createElement('div');
    item.className = 'media-item';
    item.innerHTML = `<img src="${safe}" onclick="openImageViewer('${safe}')" loading="lazy">`;
    grid.insertBefore(item, grid.firstChild);
}

// Close emoji picker when clicking outside it (and not on one of its
// own trigger buttons — the composer's emoji button, or any message's
// reaction button, both of which open/reposition it themselves).
document.addEventListener('click', (e) => {
    const picker = document.getElementById('emojiPicker');
    if (!picker || picker.classList.contains('hidden')) return;
    const isTrigger = e.target.closest('.emoji-btn, .action-btn');
    if (!picker.contains(e.target) && !isTrigger) {
        hideEmojiPicker();
    }
});

// A reaction picker is anchored to the message it was opened from at a
// single point in time — it doesn't track scroll position. Scrolling the
// message list would leave it floating next to the wrong message, so
// just close it instead.
document.addEventListener('DOMContentLoaded', () => {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;
    messagesContainer.addEventListener('scroll', () => {
        if (emojiPickerContext) hideEmojiPicker();
        updateScrollToBottomButton();
        // 150px rather than exactly 0 — triggering the fetch a little
        // before the person actually hits the very top means the next
        // page is usually already loaded (or loading) by the time they
        // get there, rather than them hitting a dead stop and having to
        // wait.
        if (messagesContainer.scrollTop < 150) {
            loadOlderMessages();
        }
    });
});

// --- Jump to bottom ---
// Also changes what happens when a new message arrives (see the
// new_message handler): previously every incoming message force-scrolled
// everyone to the bottom, which yanked the view out from under anyone who
// had scrolled up to read earlier messages. Now that only happens if you
// were already at the bottom — otherwise the message still arrives, but
// you stay where you are and this button lights up instead.
let unseenMessageCount = 0;
const SCROLL_BOTTOM_THRESHOLD = 80; // px of slack still counted as "at the bottom"

function isNearBottom(container) {
    if (!container) return true;
    return container.scrollHeight - container.scrollTop - container.clientHeight <= SCROLL_BOTTOM_THRESHOLD;
}

function updateScrollToBottomButton() {
    const container = document.getElementById('messagesContainer');
    const btn = document.getElementById('scrollToBottomBtn');
    if (!container || !btn) return;

    if (isNearBottom(container)) {
        btn.classList.add('hidden');
        unseenMessageCount = 0;
        updateScrollToBottomBadge();
    } else {
        btn.classList.remove('hidden');
    }
}

function updateScrollToBottomBadge() {
    const badge = document.getElementById('scrollToBottomBadge');
    if (!badge) return;
    if (unseenMessageCount > 0) {
        badge.textContent = unseenMessageCount > 99 ? '99+' : String(unseenMessageCount);
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function jumpToBottom() {
    scrollToBottom();
    unseenMessageCount = 0;
    updateScrollToBottomBadge();
    const btn = document.getElementById('scrollToBottomBtn');
    if (btn) btn.classList.add('hidden');
}

// --- GIF picker (GIPHY) ---
// The picker loads trending GIFs on first open, then re-queries as the
// person types (debounced). A monotonically increasing request id guards
// against an older, slower response overwriting a newer one if replies
// arrive out of order.
let gifSearchTimeout = null;
let gifRequestSeq = 0;

function toggleGifPicker() {
    const picker = document.getElementById('gifPicker');
    if (!picker) return;

    const emojiPicker = document.getElementById('emojiPicker');
    if (emojiPicker) emojiPicker.classList.add('hidden');

    const opening = picker.classList.contains('hidden');
    picker.classList.toggle('hidden');
    if (!opening) return;

    const input = document.getElementById('gifSearchInput');
    if (input && !input.dataset.bound) {
        input.dataset.bound = '1';
        input.addEventListener('input', onGifSearchInput);
        input.focus();
    }
    if (!picker.dataset.loaded) {
        picker.dataset.loaded = '1';
        fetchGifs('');
    }
}

function onGifSearchInput() {
    const input = document.getElementById('gifSearchInput');
    if (!input) return;
    clearTimeout(gifSearchTimeout);
    gifSearchTimeout = setTimeout(() => fetchGifs(input.value.trim()), 350);
}

function fetchGifs(query) {
    const grid = document.getElementById('gifGrid');
    if (!grid) return;
    const seq = ++gifRequestSeq;
    grid.innerHTML = '<div class="gif-picker-message">Loading…</div>';

    const endpoint = query ? `/api/giphy/search?q=${encodeURIComponent(query)}` : '/api/giphy/trending';
    fetch(apiUrl(endpoint))
        .then(r => r.json())
        .then(data => {
            if (seq !== gifRequestSeq) return; // superseded by a newer search
            if (data.error) {
                grid.innerHTML = `<div class="gif-picker-message">${escapeHtml(data.error)}</div>`;
                return;
            }
            renderGifGrid(data.gifs || []);
        })
        .catch(err => {
            if (seq !== gifRequestSeq) return;
            console.error('GIPHY fetch error:', err);
            grid.innerHTML = '<div class="gif-picker-message">Could not load GIFs.</div>';
        });
}

function renderGifGrid(gifs) {
    const grid = document.getElementById('gifGrid');
    if (!grid) return;
    grid.innerHTML = '';

    if (gifs.length === 0) {
        grid.innerHTML = '<div class="gif-picker-message">No GIFs found.</div>';
        return;
    }

    gifs.forEach(gif => {
        const item = document.createElement('div');
        item.className = 'gif-item';
        const img = document.createElement('img');
        img.src = safeUrl(gif.preview_url);
        img.alt = gif.title || 'GIF';
        img.loading = 'lazy';
        item.appendChild(img);
        item.onclick = () => sendGif(gif);
        grid.appendChild(item);
    });
}

function sendGif(gif) {
    const picker = document.getElementById('gifPicker');
    if (picker) picker.classList.add('hidden');

    // Sent straight over the socket, same as any other message — GIFs
    // reuse the existing file-message pipeline (image/gif mime type is
    // enough for the message list and shared-media panel to render it
    // like any other image), just with an external GIPHY URL instead of
    // an uploaded file.
    socket.emit('send_message', {
        sender: currentUser,
        content: '',
        channel: currentChannel,
        type: 'gif',
        file: {
            url: gif.url,
            filename: `${(gif.title || 'giphy').slice(0, 60)}.gif`,
            size: 0,
            mime_type: 'image/gif'
        }
    });
}

// Close GIF picker when clicking outside
document.addEventListener('click', (e) => {
    const picker = document.getElementById('gifPicker');
    const gifBtn = document.querySelector('.gif-btn');
    if (picker && gifBtn && !picker.contains(e.target) && e.target !== gifBtn && !picker.classList.contains('hidden')) {
        picker.classList.add('hidden');
    }
});
