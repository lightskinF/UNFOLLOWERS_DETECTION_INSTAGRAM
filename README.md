# UNFOLLOWERS_DETECTION_INSTAGRAM
Tecniche di Web Scraping per ottenere la lista di persone che seguiamo che a loro volta non ci seguono su Instagram.

Sono perfettamente consapevole che già qualcuno abbia potuto implementare una roba del genere, ma l'ho fatto perché tendenzialmente non mi fido di altri, e soprattutto perché ci sono app che ti scammano e si impossessano dei dati come la password, rischiando di perdere il profilo. E a dirla tutta mi piace fare web scraping, quindi ne ho approfittato per fare qualcosa che magari può essere utile a qualcuno senza rischi. 

La logica è stata questa: dato l'ID univoco dell'utente Instagram del quale vogliamo ottenere la lista delle persone che segue le quali non ricambiano, attraverso specifici endpoint, ottengo di questo utente la lista dei suoi followers e una lista di chi segue, per poi andarle a comparare e quindi creare la lista finale in cui sono inseriti gli utenti che l'utente di nostro interesse segue, le quali a loro volta non ricambiano il follow. 
Fondamentalmente, una volta individuati gli endpoint, verranno automatizzate richieste al server Instagram. Cosa importante, e qui ho sfruttato un template diciamo che già mi ero costruito per un altro progetto. Verosimilmente, alcuni server impongono un blocco al seguito di tante richieste consecutive nel giro di poco tempo da parte dello stesso utente. Per aggirare ciò ho simulato un comportamento umano, imponendo di inviare le richieste al server con un certa pausa di tot secondi di distanza una dall'altra. In più, queste richieste sono fatte sempre, in maniera random, da un diverso Browser e diverso sistema operativo. 


SETUP: 1)serve un PC. 2)Poi lo username dell'utente, da cui parte la prima richiesta per ottenerne l'ID (ragionevolmente una Primary Key che funge da Foreign Key per i suoi follower e seguiti), che ci permette poi di mandare richieste per ottenere lista followers e seguiti dato l'ID dell'utemte di nostro interesse, per poi compararle in un secondo momento.

3)Infine il cookie della sessione, vedi il video allegato. Si ottiene da Chrome DevTools nel seguente modo.
-Dal Pc, accedere a instagram e andare sul profilo di nostro interesse, che vogliamo analizzare.
-Da Windows-> premere combinazione tasti: Ctrl+Maiusc+C. Da Mac->Cmd+Opzione+C
-Esce un riquadro; dalle sezioni superiori di questo riquadro, cliccare "Network"
-Poi, tra le sezioni inferiori che escono cliccare su "Headers"
-Scorrendo in basso, sulla sinistra, nella sezione "Request Headers", comparirà la voce "Cookie"
-Selezionare interamente la stringa e fare copia e incolla nel programma quando ce lo chiederà in input.

Ovviamente basta runnare il programma, inserire username utente e cookie come spiegato sopra e poi l'algoritmo farà il resto. Alla fine del programma, comparirà un file .txt che potete salvare, in cui saranno visibili gli utenti che seguite ma che non vi seguono!


