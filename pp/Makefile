PROGRAM       = pythia

version       = JTKT
CXX           = g++
#CXXFLAGS      = -O -Wall -g -Wno-deprecated -bind_at_load -D$(version)
CXXFLAGS      = -O -Wall -g -Wno-deprecated -D$(version)  #-ggdb
LD            = g++
LDFLAGS       = -O 
SOFLAGS       = -shared
#############################################
# -bind_at_load helps to remove linker error
############################################
CXXFLAGS += $(shell root-config --cflags)
# CXXFLAGS += -t -stdlib=libc++ -pthread -std=c++20 -m64 -I/Users/dongguk-kim/alice/sw/osx_arm64/ROOT/v6-32-06-alice1-local1/include
LDFLAGS += -L$(PYTHIA8)/lib -lpythia8 -ldl
LDFLAGS  += $(shell root-config --libs) 
CXXFLAGS += $(shell $(FASTJET)/bin/fastjet-config --cxxflags )
#LDFLAGS += $(shell $(FASTJET)/fastjet-config --libs --plugins ) 
LDFLAGS += -L$(FASTJET)/lib -lfastjettools -lfastjet -lfastjetplugins -lsiscone_spherical -lsiscone
# LDFLAGS += -L$(FASTJET)/lib -lpythia8 -lfastjettools -lfastjet -lfastjetplugins -lsiscone_spherical -lsiscone
LIBDIRARCH      = lib
# LDFLAGS += -L$(PYTHIA8)/$(LIBDIRARCH) -lpythia8 -ldl
# LDFLAGS += -L$(PYTHIA8)/$(LIBDIRARCH) -ldl
INCS    += -I$(PYTHIA8)/include
CXXFLAGS  += $(INCS) 

HDRSDICT = 
           
HDRS	+= $(HDRSDICT)   nanoDict.h

# $(CXX) -lEG -lPhysics -L$(PWD) $(LDFLAGS) $(CXXFLAGS) $(OBJS) $(PROGRAM).C -o $(PROGRAM)

SRCS = $(HDRS:.h=.cxx)
OBJS = $(HDRS:.h=.o)

all:            $(PROGRAM)

$(PROGRAM):     $(OBJS) $(PROGRAM).C
		echo "@@=${LDFLAGS}"
		@echo "Linking $(PROGRAM) ..."
		$(CXX) $(CXXFLAGS) $(OBJS) $(PROGRAM).C -L$(PWD) $(LDFLAGS) -lEG -lPhysics -o $(PROGRAM)
# $(CXX) $(CXXFLAGS) $(OBJS) $(PROGRAM).C -L$(PWD) -L/Users/dongguk-kim/cernbox/workspace/Powheg/pythia8311/lib $(LDFLAGS) -lEG -lPhysics -o $(PROGRAM)
		chmod a+x $(PROGRAM)
		@echo "done"

%.cxx:


clean:
		rm -f $(OBJS) core *Dict* $(PROGRAM).o *.d $(PROGRAM) $(PROGRAM).sl

cl:  clean $(PROGRAM)

nanoDict.cc: $(HDRSDICT)
		@echo "Generating dictionary ..."
		@rm -f nanoDict.cc nanoDict.hh nanoDict.h
		@rootcint nanoDict.cc -c -D$(version) $(HDRSDICT)
