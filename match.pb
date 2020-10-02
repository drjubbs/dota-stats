syntax = "proto3";

message Hero {
	uint32 hero = 1;
	repeated uint32 items = 2 [packed=true];
    uint32 gold_spent = 3;
};

message MatchInfo {
	repeated Hero radiant_heroes = 1;
	repeated Hero dire_heroes = 2;
};
