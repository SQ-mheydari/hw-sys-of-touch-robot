\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{optodoc}[2019/12/04 OF SW Specification document]

\newcommand{\headlinecolor}{\normalcolor}

% Inherits from class book
\LoadClass[]{book}

\RequirePackage{minted}
\RequirePackage{fancyhdr}
\RequirePackage{fontspec}
\RequirePackage{eso-pic}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{enumitem}
\RequirePackage{xcolor}
\RequirePackage{background}
\RequirePackage{caption}
\RequirePackage{graphicx}
\RequirePackage{longtable}
\RequirePackage{float}
\RequirePackage{wrapfig}
\RequirePackage{rotating}
\RequirePackage[normalem]{ulem}
\RequirePackage{amsmath}
\RequirePackage{textcomp}
\RequirePackage{marvosym}
\RequirePackage{wasysym}
\RequirePackage{amssymb}
\RequirePackage{hyperref}
\RequirePackage{parskip}
\RequirePackage{awesomebox}
\RequirePackage{listings}
\RequirePackage[toc,page]{appendix}
\RequirePackage{subfig}
\RequirePackage{overpic}

\definecolor{optored}{rgb}{0.898,0.196,0.071}
\definecolor{optogreen}{rgb}{0.463,0.718,0.165}
\definecolor{optoblue}{rgb}{0,0.412,0.702}

% Adjust page margins
\setlength{\topmargin}{-0.50in}
\setlength{\headsep}{0.3in}
\setlength{\topskip}{0.10in}
\setlength{\textheight}{9.10in}
\setlength{\footskip}{20pt}
\setlength{\oddsidemargin}{0.00in}
\setlength{\evensidemargin}{0.00in}
\setlength{\textwidth}{6.50in}
\setlength{\leftmargini}{3.5em}
\setlength{\leftmarginii}{2.2em}
\setlength{\leftmarginiii}{2.2em}
\setlength{\leftmarginiv}{2.2em}
\setlength{\leftmarginv}{2.2em}
\setlength{\leftmarginvi}{2.2em}
\setlength{\leftmargin}{\leftmargini}
\setlength{\labelsep}{.5em}
\setlength{\labelwidth}{ 1.5em}
\setlength{\headheight}{25pt}

% This is a special modification for TOUCH user manual
\setlength{\parindent}{0em} 
\setlength{\parskip}{\medskipamount}

\newcommand{\optoheadingtitle}{OptoFidelity}


%% \DeclareOption{fancy}{\renewcommand{TODO}}
\DeclareOption{confidential}{\renewcommand{\optoheadingtitle}{OptoFidelity confidential}}

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

% Use sans seriff as the font
\renewcommand*\familydefault{\sfdefault}
\backgroundsetup{contents={}}

% Title page has half-page image
\newcommand\BackgroundPic{%
  \put(0,0){%
    \parbox[b][\paperheight]{\paperwidth}{%
      \centering
      \includegraphics[width=\paperwidth,height=\paperheight,%
      keepaspectratio]{ofcover}%
      \vfill
      \vfill
}}}

% Title page with title and OF Confidential logo
\renewcommand\maketitle{
  \AddToShipoutPicture*{\BackgroundPic}
  \vspace*{13cm}
  \pagestyle{empty}
  \vskip 1cm
  {\bf\Huge \textsf{\@title}}
  \vskip 0.5cm
  {\Large \textsf{\@author}}
  \vskip 0.2cm
  {\Large \textsf{\today}}
  \clearpage
  \pagestyle{fancy}
  \setcounter{page}{1}
}

%% \renewcommand{\listingscaption{\sffamily Listing}
%% \AtEndEnvironment{listing}{\vspace{-10pt}} %

% Custom table of contents on its own page
\renewcommand\tableofcontents{%
  \pagestyle{empty}
  \if@twocolumn
  \@restonecoltrue\onecolumn
  \else
  \@restonecolfalse
  \fi

  \section*{Contents}
  \@mkboth {} {}

  \@starttoc{toc}
  \if@restonecol\twocolumn\fi
  \clearpage
  \pagestyle{fancy}
  \setcounter{page}{1}
  \setenumerate{itemsep=1pt,topsep=2pt}
}
\captionsetup[table]{skip=6pt}


% Page numbering
\pagenumbering{arabic}
\setcounter{tocdepth}{2}

% Use dashes as list markers
\def\labelitemi{--}

% Set up headers
\lhead{}
\cfoot{}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\headrule}{\hbox to\headwidth{%
  \color{optoblue}\leaders\hrule height \headrulewidth\hfill}}

\renewcommand{\footrulewidth}{0.3pt}
\renewcommand{\footrule}{\hbox to\headwidth{%
  \color{optoblue}\leaders\hrule height \footrulewidth\hfill}}

% OF confidential should be visible in every page
\rhead{\color{gray}{\bf\footnotesize
    \includegraphics[scale=0.28, trim=0 0.03cm 0 0]{oflogo-trans}
    \textsf{\MakeUppercase{\optoheadingtitle}}}}

\lfoot{\color{darkgray}\textsf{www.optofidelity.com}}
\rfoot{\color{darkgray}\textsf{sales@optofidelity.com}}

\fancyhead[LO]{\textbf{\color{gray}{\sffamily \thepage }}}

% Set styling for the code blocks
\usemintedstyle{tango}

\setminted{
  frame=lines,
  framesep=2mm,
  baselinestretch=1.2,
  fontsize=\small
}

\setenumerate{itemsep=1pt,topsep=2pt}

\tolerance=1000

\RequirePackage{etoolbox}

\AtBeginEnvironment{minted}{\dontdofcolorbox}
\def\dontdofcolorbox{\renewcommand\fcolorbox[4][]{##4}}

\renewcommand{\listingscaption}{\textsf{Listing}}
\AtEndEnvironment{listing}{\vspace{-12pt}} %

% Style of lstlisting environment used for code blocks.
\lstset{ 
  backgroundcolor=\color{lightgray},
  basicstyle=\footnotesize\ttfamily
}
