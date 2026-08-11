# Annexe — Boîte à outils scientifique

*Cette annexe n'appartient à aucune strate du livre : elle ne théorise rien, elle ne spécule sur rien. Elle explique les outils mathématiques et physiques que le corps du texte réutilise, sans jamais s'arrêter pour les redéfinir. Vous pouvez la lire avant d'entamer le livre, si les formules vous intimident par principe ; la parcourir section par section au fil de votre lecture, quand une notation vous arrête ; ou l'ignorer complètement, si les équations ne vous gênent pas — rien dans le corps du texte n'exige que vous l'ayez lue. Chaque entrée part d'une image concrète avant d'introduire la notation, et se referme sur un renvoi précis vers l'endroit du livre où l'outil est effectivement utilisé.*

---

## Partie A — Petite boîte à outils mathématique

### A.1 Probabilité

Une probabilité est un nombre entre 0 et 1 qui mesure à quel point un événement est attendu, avant qu'il ne se produise. 0 : impossible. 1 : certain. 0,5 : autant de chances que son contraire. La règle la plus élémentaire, et la seule dont ce livre a vraiment besoin dès le §1, est la suivante : la probabilité que *deux* choses soient vraies à la fois ne peut jamais dépasser la probabilité que l'une d'elles, prise seule, soit vraie. « Il pleut ET il fait froid » ne peut pas être plus probable que « il pleut » tout court — chaque condition supplémentaire ne peut que restreindre, jamais élargir, l'ensemble des cas où l'affirmation complète est vraie. C'est cette règle, d'une simplicité absolue, que l'effet Linda du §1 viole systématiquement dans l'intuition humaine.

*Utilisé dans : §1, §2 (famille des biais de cognition quantique).*

### A.2 Densité de probabilité et distribution

Quand on ne peut pas énumérer un petit nombre de cas discrets (pile ou face) mais qu'on doit décrire un continuum de possibles (la position d'une bille sur une table, l'humeur d'un groupe entre deux extrêmes), il ne suffit plus de dire « telle valeur a telle probabilité » — une valeur précise, sur un continuum, a presque toujours une probabilité nulle en elle-même. On utilise à la place une *densité de probabilité* : une courbe dont la hauteur, en un point donné, indique à quel point les valeurs voisines de ce point sont probables, et dont l'aire totale (sous toute la courbe) vaut exactement 1. Une *distribution* étroite et pointue signifie un état bien déterminé, presque certain ; une distribution large et étalée signifie un état ouvert, où beaucoup de possibles restent également plausibles. C'est très exactement la différence, décrite au §3 et au §5, entre l'état analytique (distribution resserrée sur un point) et l'état de flow (distribution étalée sur une région).

*Utilisé dans : §3, §4 (paysage d'énergie), §5 (densité sur le tore), §6 (champ d'opinion Ψ).*

### A.3 Dérivée et gradient

La dérivée d'une quantité par rapport au temps, notée d(...)/dt, mesure sa vitesse de variation instantanée — pas où elle est, mais à quelle vitesse et dans quel sens elle est en train de changer. Quand on regarde l'évolution d'une phase θ(t), dθ/dt est la vitesse à laquelle cette phase tourne : c'est le cœur même de l'équation de Kuramoto au §5.

Le *gradient*, noté ∇, généralise cette idée à une quantité qui dépend de plusieurs variables à la fois — par exemple un paysage d'énergie J(x) qui dépend de la position x dans un espace à plusieurs dimensions. Le gradient ∇J en un point donné est un vecteur qui pointe dans la direction où J augmente le plus vite. Descendre une pente, c'est aller dans la direction opposée au gradient : −∇J. C'est très exactement ce que fait un système qui glisse vers un minimum d'énergie au §4, ou vers un puits de potentiel au §6 : à chaque instant, il se déplace dans la direction −∇J(x), la ligne de plus grande pente descendante.

*Utilisé dans : §5 (∂I/∂t, ∇_I(R)), §6 (∇V_prat dans l'équation du couple, D₁=−∇J dans la description du potentiel §5-§6).*

### A.4 Laplacien

Le laplacien, noté ∇² (ou Δ dans certains ouvrages — à ne pas confondre avec le Δ du double effondrement de ce livre, qui désigne un écart, pas cet opérateur), mesure à quel point la valeur d'une quantité en un point diffère de la moyenne de ses voisins immédiats. Si vous êtes exactement au creux d'un bol, entouré de partout par des points plus hauts, le laplacien y est positif ; si vous êtes au sommet d'une bosse, entouré de points plus bas, il est négatif. C'est l'outil mathématique qui décrit la *diffusion* : la chaleur se répand d'un point chaud vers ses voisins plus froids exactement selon cette logique, et c'est la même mécanique qui gouverne comment une inquiétude collective ou une rumeur se propage d'un individu à ses voisins dans le tissu social du §6 — le noyau gaussien Gσ utilisé à cet endroit est, mathématiquement, la solution de l'équation de diffusion qui a le laplacien pour moteur.

*Utilisé implicitement dans : §6 (le noyau gaussien de diffusion Gσ de la section « Le tissu social à plusieurs échelles » est gouverné par cet opérateur, même si le symbole ∇² n'apparaît pas explicitement dans le corps du texte).*

### A.5 Rotationnel

Le rotationnel, noté ∇×, mesure la tendance d'un champ de vecteurs à tourbillonner localement autour d'un point — imaginez une rivière : en la plupart des endroits l'eau coule simplement, mais dans un tourbillon, le rotationnel du courant est non nul en son centre. Ce n'est pas une simple curiosité mathématique : un théorème remarquable (Stokes) relie le rotationnel d'un champ, intégré sur toute une surface, à la circulation de ce même champ le long du contour qui borde cette surface. Or c'est exactement ce que mesure la phase de Berry introduite au §2 et formalisée au §5 : γ_Berry = ∮A(θ)dθ est une circulation — une intégrale le long d'un cycle fermé — et le théorème de Stokes dit que cette circulation n'est non nulle que si le rotationnel de A est non nul *à l'intérieur* du cycle parcouru. Autrement dit : deux systèmes intriqués qui traversent un cycle relationnel sans jamais quitter un « plan plat » (rotationnel nul) reviennent exactement à leur point de départ, sans phase accumulée ; c'est seulement en traversant une région du champ qui « tourbillonne » — une vraie tension, un vrai déplacement de cadre — que le cycle laisse une trace. Le couple étudié au §6 est une coloration particulière de ce mécanisme général, pas son origine.

*Utilisé dans : §2 (introduction du concept, θ_Berry=0 à chaque intrication), §5 (formalisation γ_Berry=∮A(θ)dθ pour deux oscillateurs couplés), §6 (coloration : application au déphasage Δθ du couple).*

### A.6 Nombre complexe

Un nombre complexe s'écrit z = a + i·b, où a et b sont deux nombres réels ordinaires et où i est un nombre dont la propriété définissante est i² = −1 — un nombre qui, multiplié par lui-même, donne −1, ce qu'aucun nombre réel ne peut faire. Loin d'être un artifice, cette construction donne un moyen économique de porter *deux* informations dans un seul objet mathématique : une grandeur (l'amplitude, ‖z‖) et un angle (la phase, θ), puisque tout nombre complexe s'écrit aussi z = r·e^(iθ), où r est la distance de z à l'origine et θ son orientation. C'est cette double capacité — porter à la fois une intensité et une orientation — qui permet, au §4, d'écrire une mémoire comme M = R + i·I (le fait sédimenté et son filtre d'interprétation dans un seul objet), et qui permet, au §5 et au §6, de décrire une phase d'oscillateur comme une rotation dans ce même plan complexe.

*Utilisé dans : §4 (M_Hopfield=R+i·I), §5, §6 (z=r·e^(iθ) pour les oscillateurs sociaux, e^(iθᵢⱼ) dans le noyau gaussien).*

### A.7 Valeurs propres et vecteurs propres

Une matrice M peut être vue comme une machine qui prend un vecteur en entrée et en renvoie un autre, généralement déformé — étiré, tourné, contracté. Mais pour presque toute matrice, il existe des directions particulières, ses *vecteurs propres* v, que la matrice ne fait que dilater ou contracter sans jamais les faire tourner : M·v = λ·v, où λ (la *valeur propre* associée) est simplement le facteur d'agrandissement ou de réduction le long de cette direction précise. Trouver les vecteurs propres d'une matrice, c'est trouver les seules directions où son action se réduit à une simple mise à l'échelle — le squelette invariant caché derrière une transformation qui, sur toute autre direction, paraît complexe.

*Utilisé dans : §4 (le paysage d'énergie de Hopfield est construit sur les valeurs propres de la matrice de poids), §5 (S_eff est calculée à partir des valeurs propres λₖ), §6 (M·v=λ·v, archétypes comme vecteurs propres).*

### A.8 Entropie

L'entropie mesure le degré de dispersion, ou d'imprévisibilité, d'une distribution. Sa formule la plus générale, due à Shannon, s'écrit S = −Σₖ pₖ ln(pₖ), où les pₖ sont les probabilités de chacun des états possibles. Si toute la probabilité est concentrée sur un seul état (pₖ=1 pour l'un, 0 pour tous les autres), l'entropie est nulle : il n'y a aucune incertitude. Si la probabilité est étalée également sur un grand nombre d'états, l'entropie est élevée : la situation est riche de possibles, mais peu prévisible. Ce livre utilise une variante spectrale de cette même idée au §5 : au lieu de probabilités pₖ, on prend les valeurs propres normalisées λₖ d'une matrice (voir A.7), et S_eff = −Σₖλₖ ln(λₖ) mesure alors combien de directions distinctes contribuent réellement à la structure de cette matrice, plutôt qu'une seule ou deux qui domineraient toutes les autres.

*Utilisé dans : §5 (S_eff, premier effondrement), §6 (héritage direct au niveau collectif).*

### A.9 Commutateur

Pour deux opérations A et B, le commutateur [Â,B̂] = ÂB̂ − B̂Â mesure si l'ordre dans lequel on les applique change le résultat. S'il est nul, l'ordre n'a aucune importance — appliquer A puis B donne exactement le même résultat que B puis A. S'il n'est pas nul, l'ordre compte fondamentalement, et c'est précisément la trace mathématique de la non-commutativité décrite au §2 : mesurer une chose puis une autre n'est pas la même opération que les mesurer dans l'ordre inverse, parce que chaque mesure *projette* l'état du système sur les axes propres à la question posée (voir §2 pour l'image des deux grilles tournées), et cette projection modifie ce qui reste disponible pour la mesure suivante.

*Utilisé dans : §2 (fondement de la non-commutativité), §6 (distinction opposition/carré dans le couple).*

### A.10 Espace de Hilbert et superposition

Un espace de Hilbert est simplement un espace vectoriel — un ensemble de directions possibles, comme les points d'une carte — muni d'une règle pour mesurer les distances et les angles entre ces directions. Ce qui le rend spécifique à la physique quantique (et à la cognition quantique opérationnelle de ce livre) est la notion de *superposition* : un état du système peut être une combinaison de plusieurs directions à la fois, sans qu'aucune ne soit encore privilégiée — pas une incertitude sur un fait déjà déterminé (« je ne sais pas encore lequel »), mais une coexistence réelle de plusieurs possibles, jusqu'à ce qu'une mesure (voir A.9) n'en sélectionne un.

*Utilisé dans : §2, §3 (l'état de flow comme distribution plutôt que point), §5 (le tore comme espace des états accessibles).*

### A.11 Exponentielle décroissante et temps caractéristique

Une quantité qui décroît de façon exponentielle, K(τ) = K₀·e^(−τ/τc), perd, à chaque intervalle de temps τc, la même *proportion* de ce qui lui restait — et non la même quantité absolue. C'est la loi de toute désexcitation naturelle : la radioactivité, le refroidissement d'une tasse de café, l'oubli d'un souvenir non renforcé. Le paramètre τc, le *temps caractéristique*, indique la vitesse de cette décroissance : plus il est petit, plus l'oubli est rapide. Ce livre en utilise une variante enrichie au §5 : K_mém(τ) = (K₀−K∞)·e^(−τ/τc) + K∞, où un résidu K∞ ne disparaît jamais complètement — c'est la différence, formalisée, entre un événement qui s'oublie totalement et un événement qui laisse une trace durable, un apprentissage.

*Utilisé dans : §5 (K_mém, sédimentation de la mémoire de friction).*

### A.12 Intrication

Au sens technique strict de la physique quantique, deux systèmes sont *intriqués* lorsque leur état conjoint ne peut plus s'écrire comme la simple juxtaposition de deux états séparés : décrire l'un correctement exige de décrire l'autre en même temps, même si les deux sont ensuite séparés dans l'espace. Ce livre, à partir du §2, élargit délibérément ce terme à toute situation où deux systèmes entrent en interaction et voient leur évolution ultérieure devenir mutuellement dépendante — une mesure sur l'un affecte ce qui peut encore être dit de l'autre. *(Strate 2 : cet élargissement est une extension du vocabulaire, pas une affirmation que toute interaction humaine relève techniquement de l'intrication quantique au sens strict.)* C'est ce sens élargi qui permet, au §2, de poser qu'une intrication établit une référence de phase (θ_Berry=0), reprise et formalisée au §5.

*Utilisé dans : §2 (introduction), §5 (Chladni/Γ, Berry), §6 (couple, tissu social).*

### A.13 Somme, intégrale, circulation

Le signe Σ (sigma majuscule) indique une somme sur un ensemble discret de termes — additionner l'effet de chaque oscillateur, de chaque voisin, de chaque contribution individuelle, comme dans l'équation de Kuramoto (§5) ou dans l'énergie de Hopfield (§4). Le signe ∫ (intégrale) fait la même chose lorsque les contributions ne sont plus discrètes mais continues — une somme sur un continuum de positions plutôt que sur une liste dénombrable, comme dans l'équation de champ du §6. Le signe ∮ (circulation, ou intégrale de contour) est une intégrale calculée le long d'un chemin fermé qui revient à son point de départ — c'est cette opération précise qui définit la phase de Berry introduite au §2 et formalisée au §5 (voir A.5 pour son lien avec le rotationnel).

*Utilisé dans : §4, §5, §6 (omniprésent).*

---

## Partie B — Le Hamiltonien, la sphère de Bloch et l'équation de Lindblad

*Cette partie détaille l'objet le plus réemployé du livre après l'oscillateur et le réseau de Hopfield : le couple formé par le Hamiltonien et l'équation de Lindblad, qui apparaît d'abord discrètement au §4, se déploie pleinement au §5 dans la construction de K_ana, et ressurgit encore au §6 dans l'équation de champ du tissu social. Comprendre ce couple, c'est comprendre le mécanisme physique unique dont toutes ces applications successives ne sont que des variations.*

### B.1 L'onde et la superposition, en image

Avant toute équation, une image suffit à poser le problème. Une corde de guitare pincée ne vibre pas selon une seule fréquence pure : elle vibre selon une combinaison de plusieurs harmoniques superposées, chacune avec son amplitude propre — c'est cette combinaison précise qui donne à chaque instrument son timbre reconnaissable. Rien, dans cette image, n'oblige à choisir *une* harmonique plutôt qu'une autre : elles coexistent toutes, simultanément, dans la vibration réelle de la corde.

La mécanique quantique — et, par extension conceptuelle assumée, la cognition quantique opérationnelle de ce livre — prend cette image au sérieux jusqu'à ses conséquences les plus profondes. L'état d'un système n'est pas, par défaut, l'une de ses configurations possibles : c'est une combinaison de toutes ses configurations possibles à la fois, chacune pondérée par une amplitude complexe (voir A.6). Ce n'est que lorsqu'une mesure a lieu que cette combinaison se résout en un résultat unique — ce que ce livre appelle, au §5, le second effondrement.

### B.2 Le système à deux niveaux et la sphère de Bloch

Le système le plus simple qui puisse porter une superposition véritable est un système à *deux* configurations possibles seulement — que l'on appelle, selon le contexte, un spin (haut/bas), un qubit (0/1), ou, dans le langage plus familier de ce livre, l'état analytique et l'état de flow (§3). Un tel système, dans son état le plus général, s'écrit |ψ⟩ = a|0⟩ + b|1⟩, une superposition des deux configurations de base pondérées par deux amplitudes complexes a et b.

Il existe une façon de représenter géométriquement *tous* les états possibles d'un tel système : la sphère de Bloch. Chaque état |ψ⟩ correspond à un point unique sur la surface d'une sphère de rayon 1. Le pôle nord représente l'état pur « 0 » ; le pôle sud, l'état pur « 1 ». Tout point sur l'équateur représente une superposition parfaitement équilibrée des deux, mais avec une phase relative différente selon sa longitude — c'est très exactement l'angle θᵢⱼ ou Δθ que ce livre réemploie au §5 et au §6 pour décrire le déphasage entre deux oscillateurs.

Ce que cette sphère rend immédiatement visible, et que les équations seules rendent plus difficile à saisir, c'est la différence entre deux types d'évolution radicalement distincts — l'objet de toute la suite de cette annexe.

### B.3 Le Hamiltonien : l'évolution qui ne perd rien

Le Hamiltonien Ĥ d'un système est l'opérateur qui gouverne son évolution dans le temps lorsque ce système est parfaitement isolé de tout environnement extérieur — l'équation de Schrödinger, iℏ∂|ψ⟩/∂t = Ĥ|ψ⟩, décrit cette évolution. Sur la sphère de Bloch, l'effet d'un Hamiltonien est d'une élégance remarquable : il fait *tourner* le point représentant l'état, à la surface même de la sphère, sans jamais le faire entrer ni sortir de cette surface. Le point reste toujours à distance 1 du centre : rien n'est perdu, rien n'est gagné, l'information totale portée par l'état est intégralement préservée — seule son orientation change.

C'est cette propriété précise — évolution réversible, qui préserve toute la superposition — que ce livre associe au flot hamiltonien H₀ dès le §5 : le flow, la pensée fluide, l'état analytique non encore contraint, sont tous décrits comme des évolutions de ce type, qui font tourner la distribution de possibles sans jamais en effacer aucun.

### B.4 Le problème : un système n'est jamais vraiment seul

Aucun système réel n'est parfaitement isolé. Un spin dans un cristal interagit, même faiblement, avec les vibrations thermiques du réseau qui l'entoure ; un qubit supraconducteur interagit, même dans les meilleures conditions expérimentales, avec les circuits électroniques qui servent à le mesurer. Cette interaction avec un environnement — qui peut lui-même contenir un nombre gigantesque de degrés de liberté, impossibles à suivre un par un — a un effet observable et irréversible sur le système lui-même : elle le fait progressivement *sortir* de la surface de la sphère de Bloch, vers son intérieur.

Un point à l'intérieur de la sphère (et non plus sur sa surface) représente un état qui n'est plus une superposition pure, mais un *mélange statistique* — le système s'est partiellement « décidé », sans pour autant s'être totalement fixé. Le centre exact de la sphère représente l'état de mélange maximal : plus aucune superposition cohérente, seulement une incertitude classique ordinaire entre les deux configurations de base. C'est ce processus, la *décohérence*, qui use progressivement la richesse d'une superposition sous l'effet du couplage à un environnement — et c'est précisément ce que ce livre appelle, au §5, le premier effondrement : la chute progressive de S_eff (voir A.8), la perte de nuance qui précède tout acte visible.

### B.5 L'équation de Lindblad : l'anatomie du dissipateur

L'équation de Lindblad est la formulation mathématique la plus générale qui décrit correctement cette évolution mixte — rotation sur la sphère ET migration vers l'intérieur — pour un système en interaction avec un environnement, tant que cette interaction reste suffisamment simple (sans mémoire à long terme de l'environnement lui-même, une hypothèse dite markovienne). Elle s'écrit, pour la matrice densité ρ qui généralise |ψ⟩ à un état pouvant être mêlé :

∂ρ/∂t = −i[Ĥ,ρ] + Σₖ γₖ(L̂ₖρL̂ₖ† − ½{L̂ₖ†L̂ₖ,ρ})

Le premier terme, −i[Ĥ,ρ], est exactement la rotation décrite en B.3 : c'est le commutateur (voir A.9) du Hamiltonien avec l'état, qui fait tourner le point sur la sphère sans jamais le faire migrer vers l'intérieur.

Le second terme est le *dissipateur* : c'est lui, et lui seul, qui fait migrer le point vers l'intérieur de la sphère. Les opérateurs L̂ₖ, appelés *opérateurs de saut*, représentent chacun un canal précis par lequel l'environnement peut « regarder » le système — une façon particulière dont une mesure ou une interaction extérieure peut extraire de l'information sur son état. Les coefficients γₖ règlent l'intensité de chacun de ces canaux : plus γₖ est grand, plus vite ce canal précis fait migrer le point vers l'intérieur de la sphère le long de la direction associée à L̂ₖ.

C'est cette anatomie précise que ce livre réemploie, sous un nom différent, dès le §5 : K_ana n'est rien d'autre qu'un tel coefficient γ, dont l'intensité règle la vitesse à laquelle le flot hamiltonien H₀ (le premier terme, la rotation pure) cède la place à un dissipateur qui fait effondrer la distribution vers un état déterminé (le second terme, l'effondrement). L'écriture compacte H_eff = H₀ − iλK_ana utilisée au §5 est une simplification légitime de cette même équation, dans le cas particulier où l'on suit seulement la trajectoire la plus probable du système plutôt que la moyenne sur tous les canaux de mesure possibles — ce que la théorie appelle une *trajectoire quantique*, une seule branche parmi l'ensemble que l'équation de Lindblad complète décrit statistiquement.

### B.6 Retour au livre : où ce mécanisme a été réemployé

Ce même couple — rotation hamiltonienne réversible d'un côté, dissipation de Lindblad irréversible de l'autre — structure trois moments distincts de ce livre, à trois échelles différentes :

Au §4, il est implicite dans le passage d'une mémoire de Hopfield à sa version complexe : le paysage d'énergie E = −½Σwᵢⱼsᵢsⱼ décrit un système qui *descend* vers un minimum, exactement comme un dissipateur de Lindblad fait migrer un point vers l'intérieur de la sphère de Bloch — l'extension complexe M=R+i·I (voir A.6) ajoute la dimension de phase que seule une description hamiltonienne complète peut porter.

Au §5, il devient explicite : H₀ est le flot hamiltonien du flow, K_ana est le coefficient de dissipation qui pousse vers le second effondrement, et le tenseur de friction Γ, avec sa sédimentation K_mém(τ) (voir A.11), est ce qui module l'intensité même de ce coefficient — l'équivalent, dans le langage de cette annexe, d'un γₖ qui n'est pas constant mais qui s'accumule avec l'historique des contacts passés.

Au §6, enfin, ce même couple est réemployé à l'échelle d'un champ continu tout entier : l'équation de diffusion du tissu social oppose un terme de propagation libre (l'équivalent collectif du flot hamiltonien) à un terme K_ana(x)·L_Lindblad[Ψ] explicitement nommé d'après ce même formalisme — la pression de conformité qui, localement, fait migrer l'opinion collective vers un état plus rigide, plus figé, moins riche en nuances.

Un rappel s'impose avant de refermer cette annexe : tout ce qui précède, dans cette Partie B, est de la physique standard, aussi solidement établie que la mécanique newtonienne — c'est la Strate 1 de ce livre, telle que définie en introduction. Ce que le corps du texte en fait ensuite — assimiler K_ana à une pression *psychologique*, Γ à une *mémoire* affective, ou le dissipateur de Lindblad à la dynamique d'un *couple* ou d'une *société* — est un geste d'un tout autre ordre : une analogie assumée, jamais une équivalence physique littérale. C'est précisément la frontière que les strates de ce livre ont pour fonction de garder visible, à chaque page.
